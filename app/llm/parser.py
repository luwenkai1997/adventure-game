import json
import re
from dataclasses import dataclass
from typing import Any, List, Tuple

from json_repair import repair_json
from pydantic import ValidationError

from app.models.chat import ChatTurnContent, ChoiceItem


class ParseError(Exception):
    def __init__(self, error_type: str, message: str, raw_content: str):
        self.error_type = error_type
        self.message = message
        self.raw_content = raw_content
        super().__init__(f"{error_type}: {message}")


class StructuredOutputParser:
    @staticmethod
    def extract_json(content: str) -> str:
        if not content or not content.strip():
            raise ValueError("LLM返回了空内容")

        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"^```\s*\n?", "", content)
        content = re.sub(r"\n?\s*```$", "", content)
        content = content.strip()

        has_bracket = "[" in content
        has_brace = "{" in content
        if has_bracket and has_brace:
            if content.find("[") < content.find("{"):
                start = content.find("[")
                end = content.rfind("]")
            else:
                start = content.find("{")
                end = content.rfind("}")
        elif has_bracket:
            start = content.find("[")
            end = content.rfind("]")
        elif has_brace:
            start = content.find("{")
            end = content.rfind("}")
        else:
            raise ValueError(f"无法找到JSON对象或数组，原始内容: {content[:300]}")

        if end <= start:
            raise ValueError(f"无法提取合法JSON片段，原始内容: {content[:300]}")

        extracted = content[start : end + 1]
        return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", extracted)

    def parse_json(self, content: str) -> Any:
        json_str = self.extract_json(content)

        # Fast path: try direct parse first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Slow path: let json-repair handle malformed JSON
        try:
            repaired = repair_json(json_str, return_objects=True, ensure_ascii=False)
            if isinstance(repaired, (dict, list)):
                return repaired
        except Exception:
            pass

        # Last resort: repair → string → parse
        try:
            repaired_str = repair_json(json_str, ensure_ascii=False)
            return json.loads(repaired_str)
        except Exception as exc:
            raise ValueError(
                f"JSON解析失败: {exc}\n解析字符串: {json_str[:300]}\n原始内容: {content[:300]}"
            )


class ChatTurnParser:
    def __init__(self, json_parser: StructuredOutputParser):
        self.json_parser = json_parser

    def _convert_legacy_choices(self, choices: List[str]) -> List[ChoiceItem]:
        return [ChoiceItem(text=text, check=None) for text in choices]

    def parse(self, raw_content: str) -> ChatTurnContent:
        try:
            parsed = self.json_parser.parse_json(raw_content)
        except ValueError as exc:
            raise ParseError("JSON_SYNTAX", str(exc), raw_content) from exc

        if "choices" in parsed and isinstance(parsed["choices"], list):
            if parsed["choices"] and isinstance(parsed["choices"][0], str):
                parsed["choices"] = self._convert_legacy_choices(parsed["choices"])

        try:
            return ChatTurnContent(**parsed)
        except ValidationError as exc:
            raise ParseError("VALIDATION", str(exc), raw_content) from exc

    def get_repair_prompt(self, raw_content: str) -> str:
        return f"""你之前的输出格式不正确。请严格按照JSON格式返回，只能包含合法的JSON，不要有任何其他文字。

原始输出内容：
{raw_content[:1000]}

请重新输出，必须严格遵循以下JSON Schema：

{{
  "scene": "剧情描述字符串（3-6句）",
  "log": "一句话概括本章发生的事",
  "choices": [
    {{
      "text": "选项文本",
      "tendency": ["倾向标签1", "倾向标签2"],
      "is_key_decision": false,
      "consequence_hint": "后果预览（可选）",
      "check": null 或者 {{
        "attribute": "属性名如strength",
        "skill": "技能名（可选）",
        "difficulty": 难度数字8-20之间,
        "description": "检定描述（可选）"
      }},
      "check_optional": true,
      "check_prompt": "提示文字（可选）"
    }}
  ],
  "relationship_changes": [
    {{
      "character_name": "NPC名称",
      "change_type": "+",
      "value": 10,
      "reason": "原因"
    }}
  ]
}}

如果是结局，返回：
{{
  "scene": "完整结局描述",
  "log": "冒险终章",
  "ending": "好结局/中立结局/坏结局"
}}

倾向标签从以下维度选择：勇敢/谨慎、善良/冷酷、理性/感性、正义/自利、仁慈/残忍、坦诚/狡诈

请直接输出JSON，不要用markdown代码块包裹，不要有任何解释。
"""
