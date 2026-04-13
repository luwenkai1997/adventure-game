import json
import re
from typing import Any

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

def parse_json_response(content: str) -> Any:
    if not content or not content.strip():
        raise Exception("LLM返回了空内容")

    original_content = content
    json_str = extract_json(content)

    parsed = None
    error_msg = ""

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        error_msg = str(e)

    if parsed is None:
        repaired_json = repair_json(json_str)
        try:
            parsed = json.loads(repaired_json)
        except json.JSONDecodeError as e:
            error_msg = f"修复后仍失败: {str(e)}"

    if parsed is None:
        json_str_backup = json_str.replace("'", '"')
        try:
            parsed = json.loads(json_str_backup)
        except json.JSONDecodeError:
            pass

    if parsed is None:
        repaired_backup = repair_json(json_str_backup)
        try:
            parsed = json.loads(repaired_backup)
        except json.JSONDecodeError:
            pass

    if parsed is None:
        raise Exception(
            f"JSON解析失败: {error_msg}\n解析字符串: {json_str[:300]}\n原始内容: {original_content[:300]}"
        )

    return parsed
