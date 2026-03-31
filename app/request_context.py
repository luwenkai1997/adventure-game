from contextvars import ContextVar, Token
from typing import Any, Dict, Optional

session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
file_io_cache_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "file_io_cache", default=None
)


def get_current_session_id() -> Optional[str]:
    return session_id_ctx.get()


def set_current_session_id(session_id: Optional[str]) -> None:
    session_id_ctx.set(session_id)


def get_request_id() -> Optional[str]:
    return request_id_ctx.get()


def set_request_id(request_id: Optional[str]) -> None:
    request_id_ctx.set(request_id)


def begin_file_io_cache() -> Token:
    return file_io_cache_ctx.set({})


def reset_file_io_cache(token: Token) -> None:
    file_io_cache_ctx.reset(token)


def get_file_io_cache() -> Optional[Dict[str, Any]]:
    return file_io_cache_ctx.get()
