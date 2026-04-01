import json
import re
from typing import Tuple, Optional, List
from pydantic import ValidationError
from app.models.chat import ChatTurnContent, ChoiceItem
from app.utils.json_utils import extract_json, repair_json


class ParseError(Exception):
    def __init__(self, error_type: str, message: str, raw_content: str):
        self.error_type = error_type
        self.message = message
        self.raw_content = raw_content
        super().__init__(f"{error_type}: {message}")



def convert_legacy_choices(choices: List[str]) -> List[ChoiceItem]:
    return [ChoiceItem(text=text, check=None) for text in choices]


def parse_chat_output(raw_content: str) -> Tuple[ChatTurnContent, bool]:
    json_str = extract_json(raw_content)

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        repaired = repair_json(json_str)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as e2:
            raise ParseError("JSON_SYNTAX", str(e2), raw_content)

    if "choices" in parsed and isinstance(parsed["choices"], list):
        if len(parsed["choices"]) > 0 and isinstance(parsed["choices"][0], str):
            parsed["choices"] = convert_legacy_choices(parsed["choices"])

    try:
        content = ChatTurnContent(**parsed)
        return content, False
    except ValidationError as e:
        raise ParseError("VALIDATION", str(e), raw_content)


def get_repair_prompt(raw_content: str) -> str:
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
