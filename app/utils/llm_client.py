import json
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
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_str = content
        brace_start = json_str.find('[')
        brace_end = json_str.rfind(']') + 1
        if brace_start != -1 and brace_end > brace_start:
            json_str = json_str[brace_start:brace_end]
        else:
            brace_start = json_str.find('{')
            brace_end = json_str.rfind('}') + 1
            if brace_start != -1 and brace_end > brace_start:
                json_str = json_str[brace_start:brace_end]
        return json.loads(json_str)
