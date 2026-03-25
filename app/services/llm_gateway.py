import time
import requests
import json
from typing import Optional, Generator, List, Dict, Any, Callable
from app.config import (
    API_BASE_URL,
    API_MODEL,
    API_KEY,
    API_STREAMING_ENABLED,
    API_TIMEOUT,
)


_active_cancellations: Dict[str, bool] = {}


def register_cancellation(request_id: str) -> None:
    _active_cancellations[request_id] = False


def cancel_request(request_id: str) -> None:
    _active_cancellations[request_id] = True


def is_cancelled(request_id: str) -> bool:
    return _active_cancellations.get(request_id, False)


def clean_cancellation(request_id: str) -> None:
    _active_cancellations.pop(request_id, None)


def call_llm_with_retry(
    prompt: str,
    system_prompt: Optional[str] = None,
    request_id: Optional[str] = None,
    max_retries: int = 2,
    timeout: int = API_TIMEOUT,
) -> str:
    last_error = None

    for attempt in range(max_retries):
        try:
            if request_id and is_cancelled(request_id):
                raise RuntimeError("请求已取消")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            headers = {
                "Content-Type": "application/json",
            }
            if API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"

            payload = {
                "model": API_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "stream": False,
            }

            response = requests.post(
                f"{API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            if request_id:
                clean_cancellation(request_id)

            return content

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

    if request_id:
        clean_cancellation(request_id)
    raise last_error


def stream_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    request_id: Optional[str] = None,
    timeout: int = API_TIMEOUT,
) -> Generator[str, None, None]:
    if request_id:
        register_cancellation(request_id)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Content-Type": "application/json",
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    payload = {
        "model": API_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if request_id and is_cancelled(request_id):
                break

            if not line:
                continue
            if line.startswith("data: "):
                line = line[6:]
            if line == "[DONE]":
                break

            try:
                data = json.loads(line)
                if "choices" in data and len(data["choices"]) > 0:
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
            except Exception:
                continue

    finally:
        if request_id:
            clean_cancellation(request_id)
