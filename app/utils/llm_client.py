import json
import re
import time
import os
import requests
from requests.exceptions import (
    RequestException,
    ChunkedEncodingError,
    Timeout,
    ConnectionError,
)
from typing import Any, Optional
from datetime import datetime
from app.config import API_BASE_URL, API_MODEL, API_KEY

MAX_TOKENS_LIMIT = 16384
MAX_RETRIES = 3
RETRY_DELAY = 2


def get_llm_log_path() -> str:
    try:
        from app.utils.file_storage import get_current_game, get_game_dir
        game_id = get_current_game()
        if game_id:
            game_dir = get_game_dir(game_id)
            return os.path.join(game_dir, "llm-log.md")
    except:
        pass
    return None


def log_llm_call(
    method_name: str,
    request_messages: list,
    request_params: dict,
    response_content: str,
    response_usage: Optional[dict] = None,
    error: Optional[str] = None,
):
    log_path = get_llm_log_path()
    if not log_path:
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    log_entry = f"""
---

## {timestamp}

### 方法名称
`{method_name}`

### 请求参数
```json
{json.dumps(request_params, ensure_ascii=False, indent=2)}
```

### 发送消息
```json
{json.dumps(request_messages, ensure_ascii=False, indent=2)}
```

### 响应内容
```
{response_content[:2000] if response_content else '(无)'}
```
"""
    
    if response_usage:
        log_entry += f"""
### Token使用统计
```json
{json.dumps(response_usage, ensure_ascii=False, indent=2)}
```
"""
    
    if error:
        log_entry += f"""
### 错误信息
```
{error}
```
"""
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[LLM日志] 写入失败: {e}")


def call_llm(
    prompt: str,
    system_prompt: str = None,
    timeout: int = 120,
    max_tokens: int = MAX_TOKENS_LIMIT,
    method_name: str = "call_llm",
) -> str:
    if system_prompt is None:
        system_prompt = "你是一个AI助手。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    payload = {
        "model": API_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }

    request_params = {
        "model": API_MODEL,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "stream": True,
    }

    print(f"[LLM] 方法: {method_name}")
    print(f"[LLM] API_BASE_URL: {API_BASE_URL}")
    print(f"[LLM] API_MODEL: {API_MODEL}")
    print(f"[LLM] max_tokens: {max_tokens}")
    print(f"[LLM] 使用流式响应模式")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=(30, timeout),
                stream=True,
            )

            print(f"[LLM] Response Status: {response.status_code}")

            if response.status_code != 200:
                error_text = ""
                try:
                    error_text = response.text[:500]
                except:
                    error_text = "无法读取错误响应"
                print(f"[LLM] Error: {error_text}")
                raise Exception(f"API请求失败: {response.status_code} - {error_text}")

            full_content = ""
            usage_info = None
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                content = chunk["choices"][0]["delta"]["content"]
                                full_content += content
                            if chunk.get("usage"):
                                usage_info = chunk["usage"]
                        except json.JSONDecodeError:
                            continue

            print(f"[LLM] Response Content Length: {len(full_content)}")
            print(f"[LLM] Response Preview: {full_content[:200]}...")
            
            log_llm_call(
                method_name=method_name,
                request_messages=messages,
                request_params=request_params,
                response_content=full_content,
                response_usage=usage_info,
            )
            
            return full_content

        except (ChunkedEncodingError, Timeout, ConnectionError, RequestException) as e:
            last_error = e
            print(
                f"API请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {type(e).__name__}: {str(e)[:100]}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            continue
        except Exception as e:
            log_llm_call(
                method_name=method_name,
                request_messages=messages,
                request_params=request_params,
                response_content=None,
                error=str(e),
            )
            raise e

    error_msg = f"API请求失败，已重试{MAX_RETRIES}次: {last_error}"
    log_llm_call(
        method_name=method_name,
        request_messages=messages,
        request_params=request_params,
        response_content=None,
        error=error_msg,
    )
    raise Exception(error_msg)


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
