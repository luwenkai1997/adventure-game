import json
import re
import requests
from typing import Any
from app.config import API_BASE_URL, API_MODEL, API_KEY


def call_llm(prompt: str, system_prompt: str = None, timeout: int = 120) -> str:
    if system_prompt is None:
        system_prompt = "你是一个AI助手。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }

    payload = {
        'model': API_MODEL,
        'messages': messages
    }

    response = requests.post(
        f'{API_BASE_URL}/chat/completions',
        headers=headers,
        json=payload,
        timeout=timeout
    )

    if response.status_code != 200:
        raise Exception(f"API请求失败: {response.status_code}")

    result = response.json()
    return result['choices'][0]['message']['content']


def parse_json_response(content: str) -> Any:
    if not content or not content.strip():
        raise Exception("LLM返回了空内容")

    original_content = content
    json_str = content.strip()

    json_str = re.sub(r'^```(?:json)?\s*\n?', '', json_str)
    json_str = re.sub(r'^```\s*\n?', '', json_str)
    json_str = re.sub(r'\n?\s*```$', '', json_str)

    json_str = json_str.strip()

    has_bracket = '[' in json_str
    has_brace = '{' in json_str

    if has_bracket and has_brace:
        if json_str.find('[') < json_str.find('{'):
            brace_start = json_str.find('[')
            brace_end = json_str.rfind(']')
            if brace_end > brace_start:
                json_str = json_str[brace_start:brace_end + 1]
        else:
            brace_start = json_str.find('{')
            brace_end = json_str.rfind('}')
            if brace_end > brace_start:
                json_str = json_str[brace_start:brace_end + 1]
    elif has_bracket:
        brace_start = json_str.find('[')
        brace_end = json_str.rfind(']')
        if brace_end > brace_start:
            json_str = json_str[brace_start:brace_end + 1]
    elif has_brace:
        brace_start = json_str.find('{')
        brace_end = json_str.rfind('}')
        if brace_end > brace_start:
            json_str = json_str[brace_start:brace_end + 1]
    else:
        raise Exception(f"无法找到JSON对象或数组，原始内容: {original_content[:300]}")

    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r',\s*\}', '}', json_str)

    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

    parsed = None
    error_msg = ""

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        error_msg = str(e)

    if parsed is None:
        json_str_backup = json_str.replace("'", '"')
        try:
            parsed = json.loads(json_str_backup)
        except json.JSONDecodeError:
            pass

    if parsed is None:
        raise Exception(f"JSON解析失败: {error_msg}\n解析字符串: {json_str[:200]}\n原始内容: {original_content[:200]}")

    return parsed
