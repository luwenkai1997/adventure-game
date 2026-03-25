"""Shared httpx.AsyncClient for outbound HTTP (LLM API)."""
from typing import Optional

import httpx

_http_client: Optional[httpx.AsyncClient] = None


async def init_http_client() -> None:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError(
            "HTTP client not initialized; ensure application lifespan runs (see server.py)."
        )
    return _http_client
