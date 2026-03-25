import json
import re
from typing import Tuple, Optional, List, Any
from pydantic import ValidationError
from app.models.chat import ChatTurnContent, ChoiceItem, CheckSpec


class ParseError(Exception):
    def __init__(self, error_type: str, message: str, raw_content: str):
        self.error_type = error_type
        self.message = message
        self.raw_content = raw_content
        super().__init__(f"{error_type}: {message}")


def repair_json(s: str) -> str:
    s = re.sub(r",\s*([\]}])", r"\1", s)

    last_comma = s.rfind(",")
    last_quote_close = s.rfind('"')

    if last_comma > 0 and (last_quote_close < last_comma or last_quote_close == -1):
        s = s[:last_comma]

    if s.rstrip().endswith(":"):
        s = s.rstrip()[:-1]

    if s.rstrip().endswith('"') and s.count('"') % 2 != 0:
        s = s.rstrip()[:-1]

    open_braces = s.count("{")
    close_braces = s.count("}")
    if open_braces > close_braces:
        s += "}" * (open_braces - close_braces)

    open_brackets = s.count("[")
    close_brackets = s.count("]")
    if open_brackets > close_brackets:
        s += "]" * (open_brackets - close_brackets)

    s = re.sub(r",\s*([\]}])", r"\1", s)

    while s and s[-1] in [",", ":", " "]:
        s = s[:-1]

    return s


def extract_json(content: str) -> str:
    if not content or not content.strip():
        return ""

    content = content.strip()

    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"^```\s*\n?", "", content)
    content = re.sub(r"\n?\s*```$", "", content)

    content = content.strip()

    has_bracket = "[" in content
    has_brace = "{" in content

    if has_bracket and has_brace:
        if content.find("[") < content.find("{"):
            brace_start = content.find("[")
            brace_end = content.rfind("]")
            if brace_end > brace_start:
                content = content[brace_start : brace_end + 1]
        else:
            brace_start = content.find("{")
            brace_end = content.rfind("}")
            if brace_end > brace_start:
                content = content[brace_start : brace_end + 1]
    elif has_bracket:
        brace_start = content.find("[")
        brace_end = content.rfind("]")
        if brace_end > brace_start:
            content = content[brace_start : brace_end + 1]
    elif has_brace:
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_end > brace_start:
            content = content[brace_start : brace_end + 1]

    content = re.sub(r",\s*]", "]", content)
    content = re.sub(r",\s*}", "}", content)

    content = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", content)

    return content


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
      "check": null 或者 {{
        "attribute": "属性名如strength",
        "skill": "技能名（可选）",
        "difficulty": 难度数字8-20之间,
        "description": "检定描述（可选）"
      }},
      "check_optional": true,
      "check_prompt": "提示文字（可选）"
    }}
  ]
如果是结局，返回：
{{
  "scene": "完整结局描述",
  "log": "冒险终章",
  "ending": "好结局/中立结局/坏结局"
}}

请直接输出JSON，不要用markdown代码块包裹，不要有任何解释。
"""
