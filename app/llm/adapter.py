import asyncio
import json
import logging
import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import API_BASE_URL, API_KEY, API_MODEL, API_MODEL_UTILITY, API_TIMEOUT
from app.game_context import GameContext
from app.http_client import get_http_client
from app.llm.parser import ChatTurnParser, ParseError, StructuredOutputParser

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    timeout: int = API_TIMEOUT


@dataclass(frozen=True)
class StreamEvent:
    type: str
    request_id: str
    content: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    repaired: Optional[bool] = None
    payload: Optional[Dict[str, Any]] = None


class TransportClient:
    def __init__(self):
        self._active_cancellations: Dict[str, bool] = {}

    def register_cancellation(self, request_id: str) -> None:
        self._active_cancellations[request_id] = False

    def cancel_request(self, request_id: str) -> None:
        self._active_cancellations[request_id] = True

    def is_cancelled(self, request_id: str) -> bool:
        return self._active_cancellations.get(request_id, False)

    def clean_cancellation(self, request_id: str) -> None:
        self._active_cancellations.pop(request_id, None)

    def normalize_messages(
        self,
        messages: Optional[List[Dict[str, Any]]],
        prompt: str,
        system_prompt: Optional[str],
    ) -> List[Dict[str, str]]:
        if messages is not None:
            normalized = []
            for message in messages:
                role = message.get("role")
                content = message.get("content")
                if role not in ("system", "user", "assistant") or content is None:
                    continue
                normalized.append({"role": role, "content": str(content)})
            if not normalized:
                raise ValueError("LLM messages list is empty or invalid")
            return normalized

        built = []
        if system_prompt:
            built.append({"role": "system", "content": system_prompt})
        built.append({"role": "user", "content": prompt})
        return built

    async def post(
        self,
        payload: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        client = get_http_client()
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        response = await client.post(
            f"{API_BASE_URL.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )
        response.raise_for_status()
        return response.json()

    async def stream(
        self,
        payload: Dict[str, Any],
        timeout: int,
    ) -> AsyncIterator[str]:
        client = get_http_client()
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        async with client.stream(
            "POST",
            f"{API_BASE_URL.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line == "[DONE]":
                    break
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "choices" in data and data["choices"]:
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]


class LLMAdapter:
    def __init__(
        self,
        transport: TransportClient,
        json_parser: StructuredOutputParser,
        chat_parser: ChatTurnParser,
        llm_log_repository,
    ):
        self.transport = transport
        self.json_parser = json_parser
        self.chat_parser = chat_parser
        self.llm_log_repository = llm_log_repository

    def cancel_request(self, request_id: str) -> None:
        self.transport.cancel_request(request_id)

    def is_cancelled(self, request_id: str) -> bool:
        return self.transport.is_cancelled(request_id)

    def _log_call(
        self,
        ctx: Optional[GameContext],
        method_name: str,
        request_messages: List[Dict[str, Any]],
        request_params: Dict[str, Any],
        response_content: str,
        response_usage: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
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
        self.llm_log_repository.append(ctx, log_entry)

    async def generate_text(
        self,
        ctx: Optional[GameContext],
        prompt: str = "",
        system_prompt: Optional[str] = None,
        timeout: int = API_TIMEOUT,
        max_tokens: Optional[int] = 16384,
        method_name: str = "generate_text",
        request_id: Optional[str] = None,
        max_retries: int = 2,
        messages: Optional[List[Dict[str, Any]]] = None,
        use_utility_model: bool = False,
    ) -> str:
        message_list = self.transport.normalize_messages(messages, prompt, system_prompt)
        last_error: Optional[Exception] = None
        model = API_MODEL_UTILITY if use_utility_model else API_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "messages": message_list,
            "temperature": 0.7,
            "stream": False,
        }
        if max_tokens is not None and 0 < max_tokens <= 200000:
            payload["max_tokens"] = max_tokens

        for attempt in range(max_retries):
            try:
                if request_id and self.transport.is_cancelled(request_id):
                    raise RuntimeError("请求已取消")
                data = await self.transport.post(payload, timeout)
                content = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage")
                self._log_call(
                    ctx,
                    method_name,
                    message_list,
                    {"model": model, "stream": False, "max_tokens": payload.get("max_tokens")},
                    content,
                    response_usage=usage,
                )
                if request_id:
                    self.transport.clean_cancellation(request_id)
                return content
            except httpx.HTTPStatusError as exc:
                # 4xx errors other than 429 (rate-limit) are permanent failures — don't retry.
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    self._log_call(
                        ctx,
                        method_name,
                        message_list,
                        {"model": payload.get("model"), "stream": False},
                        "",
                        error=f"HTTP {status}: {exc}",
                    )
                    raise
                last_error = exc
                logger.warning(
                    "LLM %s attempt %s/%s: HTTP %s",
                    method_name,
                    attempt + 1,
                    max_retries,
                    status,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(30.0, (2**attempt) * (0.5 + random.random())))
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM %s attempt %s/%s: %s",
                    method_name,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(30.0, (2**attempt) * (0.5 + random.random())))

        self._log_call(
            ctx,
            method_name,
            message_list,
            {"model": model, "stream": False, "max_tokens": payload.get("max_tokens")},
            "",
            error=str(last_error) if last_error else "unknown error",
        )
        if request_id:
            self.transport.clean_cancellation(request_id)
        if last_error is not None:
            raise last_error
        raise RuntimeError("LLM call failed with no error detail")

    def parse_json(self, content: str) -> Any:
        return self.json_parser.parse_json(content)

    async def generate_json(
        self,
        ctx: Optional[GameContext],
        prompt: str = "",
        system_prompt: Optional[str] = None,
        timeout: int = API_TIMEOUT,
        max_tokens: Optional[int] = 16384,
        method_name: str = "generate_json",
        parser=None,
        request_id: Optional[str] = None,
        max_retries: int = 2,
        messages: Optional[List[Dict[str, Any]]] = None,
        use_utility_model: bool = False,
    ) -> Any:
        content = await self.generate_text(
            ctx=ctx,
            prompt=prompt,
            system_prompt=system_prompt,
            timeout=timeout,
            max_tokens=max_tokens,
            method_name=method_name,
            request_id=request_id,
            max_retries=max_retries,
            messages=messages,
            use_utility_model=use_utility_model,
        )
        parse_fn = parser or self.json_parser.parse_json
        return parse_fn(content)

    async def _validate_or_repair_chat_turn(
        self,
        ctx: Optional[GameContext],
        raw_content: str,
        request_id: Optional[str],
        repair_method_name: str,
    ):
        attempts = 0
        last_error: Optional[ParseError] = None
        content = raw_content
        while attempts <= 2:
            try:
                return self.chat_parser.parse(content), attempts > 0
            except ParseError as exc:
                last_error = exc
                attempts += 1
                if attempts > 2:
                    break
                repair_prompt = self.chat_parser.get_repair_prompt(content)
                content = await self.generate_text(
                    ctx,
                    prompt=repair_prompt,
                    method_name=repair_method_name,
                    request_id=request_id,
                    use_utility_model=True,
                )
        if last_error is not None:
            raise last_error
        raise ParseError("VALIDATION", "parse failed", raw_content)

    async def generate_chat_turn(
        self,
        ctx: Optional[GameContext],
        messages: List[Dict[str, Any]],
        request_id: Optional[str] = None,
        method_name: str = "game_chat",
    ):
        raw_content = await self.generate_text(
            ctx=ctx,
            messages=messages,
            method_name=method_name,
            request_id=request_id,
        )
        parsed_content, repaired = await self._validate_or_repair_chat_turn(
            ctx, raw_content, request_id, "chat_repair"
        )
        return parsed_content, raw_content, repaired

    async def stream_text(
        self,
        ctx: Optional[GameContext],
        request_id: str,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        timeout: int = API_TIMEOUT,
        max_tokens: Optional[int] = 16384,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        self.transport.register_cancellation(request_id)
        message_list = self.transport.normalize_messages(messages, prompt, system_prompt)
        payload: Dict[str, Any] = {
            "model": API_MODEL,
            "messages": message_list,
            "temperature": 0.7,
            "stream": True,
        }
        if max_tokens is not None and 0 < max_tokens <= 200000:
            payload["max_tokens"] = max_tokens

        try:
            async for chunk in self.transport.stream(payload, timeout):
                if self.transport.is_cancelled(request_id):
                    break
                yield chunk
        finally:
            self.transport.clean_cancellation(request_id)

    async def stream_chat_turn(
        self,
        ctx: Optional[GameContext],
        messages: List[Dict[str, Any]],
        request_id: Optional[str] = None,
    ) -> AsyncIterator[StreamEvent]:
        rid = request_id or str(uuid.uuid4())
        full_content = ""
        try:
            async for chunk in self.stream_text(ctx, rid, messages=messages):
                full_content += chunk
                if self.is_cancelled(rid):
                    yield StreamEvent(type="cancelled", request_id=rid)
                    return
                yield StreamEvent(type="chunk", request_id=rid, content=chunk)

            parsed, repaired = await self._validate_or_repair_chat_turn(
                ctx, full_content, rid, "chat_repair_stream"
            )
            yield StreamEvent(
                type="done",
                request_id=rid,
                success=True,
                repaired=repaired,
                payload=parsed.model_dump(),
            )
        except ParseError as exc:
            yield StreamEvent(
                type="error",
                request_id=rid,
                success=False,
                error=f"解析失败: {exc.message}",
            )
        except Exception as exc:
            yield StreamEvent(
                type="error",
                request_id=rid,
                success=False,
                error=str(exc),
            )
