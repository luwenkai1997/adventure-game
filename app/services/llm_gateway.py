import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import (
    API_BASE_URL,
    API_MODEL,
    API_KEY,
    API_TIMEOUT,
)
from app.http_client import get_http_client

logger = logging.getLogger(__name__)

MAX_TOKENS_LIMIT = 16384

_active_cancellations: Dict[str, bool] = {}


def register_cancellation(request_id: str) -> None:
    _active_cancellations[request_id] = False


def cancel_request(request_id: str) -> None:
    _active_cancellations[request_id] = True


def is_cancelled(request_id: str) -> bool:
    return _active_cancellations.get(request_id, False)


def clean_cancellation(request_id: str) -> None:
    _active_cancellations.pop(request_id, None)


def _normalize_messages(
    messages, prompt: str, system_prompt,
):
    if messages is not None:
        out = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            if role not in ("system", "user", "assistant") or content is None:
                continue
            out.append({"role": role, "content": str(content)})
        if not out:
            raise ValueError("LLM messages list is empty or invalid")
        return out
    built = []
    if system_prompt:
        built.append({"role": "system", "content": system_prompt})
    built.append({"role": "user", "content": prompt})
    return built


def get_llm_log_path():
    try:
        from app.utils.file_storage import get_current_game
        from app.utils.game_manager import get_game_dir
        game_id = get_current_game()
        if game_id:
            return os.path.join(get_game_dir(game_id), "llm-log.md")
    except Exception:
        return None
    return None


def log_llm_call(method_name, request_messages, request_params, response_content, response_usage=None, error=None):
    log_path = get_llm_log_path()
    if not log_path:
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    body = f"\n---\n## {ts}\n`{method_name}`\n{response_content[:2000] if response_content else ''}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        logger.warning("LLM log write failed: %s", e)


def parse_json_response(content: str):
    if not content or not content.strip():
        raise ValueError("empty")
    from app.utils.json_utils import parse_json_response as pjr
    return pjr(content)


async def call_llm_with_retry(
    prompt: str = "",
    system_prompt = None,
    request_id = None,
    max_retries: int = 4,
    timeout: int = API_TIMEOUT,
    messages = None,
    max_tokens = None,
    method_name: str = "call_llm_with_retry",
) -> str:
    client = get_http_client()
    last_error = None
    msg_list = _normalize_messages(messages, prompt, system_prompt)
    for attempt in range(max_retries):
        try:
            if request_id and is_cancelled(request_id):
                raise RuntimeError("请求已取消")
            headers = {"Content-Type": "application/json"}
            if API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            payload = {"model": API_MODEL, "messages": msg_list, "temperature": 0.7, "stream": False}
            if max_tokens is not None and 0 < max_tokens <= 200000:
                payload["max_tokens"] = max_tokens
            base = API_BASE_URL.rstrip("/")
            response = await client.post(
                f"{base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(timeout),
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage")
            log_llm_call(method_name, msg_list, {"model": API_MODEL}, content, response_usage=usage)
            if request_id:
                clean_cancellation(request_id)
            return content
        except Exception as e:
            last_error = e
            logger.warning("LLM %s attempt %s/%s: %s", method_name, attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                await asyncio.sleep(min(30.0, (2 ** attempt) * (0.5 + random.random())))
                continue
    if request_id:
        clean_cancellation(request_id)
    if last_error is not None:
        raise last_error
    raise RuntimeError("LLM call failed with no error detail")


async def stream_llm(
    prompt: str = "",
    system_prompt = None,
    request_id = None,
    timeout: int = API_TIMEOUT,
    messages = None,
    max_tokens = None,
):
    if request_id:
        register_cancellation(request_id)
    client = get_http_client()
    msg_list = _normalize_messages(messages, prompt, system_prompt)
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    payload = {"model": API_MODEL, "messages": msg_list, "temperature": 0.7, "stream": True}
    if max_tokens is not None and 0 < max_tokens <= 200000:
        payload["max_tokens"] = max_tokens
    base = API_BASE_URL.rstrip("/")
    try:
        async with client.stream(
            "POST",
            f"{base}/chat/completions",
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
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
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    finally:
        if request_id:
            clean_cancellation(request_id)



async def call_llm(
    prompt: str = "",
    system_prompt = None,
    timeout: int = API_TIMEOUT,
    max_tokens: int = MAX_TOKENS_LIMIT,
    method_name: str = "call_llm",
    request_id = None,
    max_retries: int = 2,
    messages = None,
) -> str:
    mt = max_tokens if max_tokens and max_tokens < 200000 else None
    return await call_llm_with_retry(
        prompt=prompt,
        system_prompt=system_prompt,
        request_id=request_id,
        max_retries=max_retries,
        timeout=timeout,
        messages=messages,
        max_tokens=mt,
        method_name=method_name,
    )
