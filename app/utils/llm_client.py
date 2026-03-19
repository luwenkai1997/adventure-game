import json
import re
import requests
from typing import Any
from app.config import API_BASE_URL, API_MODEL, API_KEY


def call_llm(
    prompt: str, system_prompt: str = None, timeout: int = 120, max_tokens: int = 4000
) -> str:
    if system_prompt is None:
        system_prompt = "你是一个AI助手。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    payload = {"model": API_MODEL, "messages": messages, "max_tokens": max_tokens}

    response = requests.post(
        f"{API_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    if response.status_code != 200:
        raise Exception(f"API请求失败: {response.status_code}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


def parse_json_response(content: str) -> Any:
    if not content or not content.strip():
        raise Exception("LLM返回了空内容")

    original_content = content
    json_str = content.strip()

    json_str = re.sub(r"^```(?:json)?\s*\n?", "", json_str)
    json_str = re.sub(r"^```\s*\n?", "", json_str)
    json_str = re.sub(r"\n?\s*```$", "", json_str)

    json_str = json_str.strip()

    has_bracket = "[" in json_str
    has_brace = "{" in json_str

    if has_bracket and has_brace:
        if json_str.find("[") < json_str.find("{"):
            brace_start = json_str.find("[")
            brace_end = json_str.rfind("]")
            if brace_end > brace_start:
                json_str = json_str[brace_start : brace_end + 1]
        else:
            brace_start = json_str.find("{")
            brace_end = json_str.rfind("}")
            if brace_end > brace_start:
                json_str = json_str[brace_start : brace_end + 1]
    elif has_bracket:
        brace_start = json_str.find("[")
        brace_end = json_str.rfind("]")
        if brace_end > brace_start:
            json_str = json_str[brace_start : brace_end + 1]
    elif has_brace:
        brace_start = json_str.find("{")
        brace_end = json_str.rfind("}")
        if brace_end > brace_start:
            json_str = json_str[brace_start : brace_end + 1]
    else:
        raise Exception(f"无法找到JSON对象或数组，原始内容: {original_content[:300]}")

    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = re.sub(r",\s*\}", "}", json_str)

    json_str = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str)

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
