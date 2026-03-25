from contextvars import ContextVar
from typing import Optional

session_id_ctx: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


def get_current_session_id() -> Optional[str]:
    return session_id_ctx.get()


def set_current_session_id(session_id: Optional[str]) -> None:
    session_id_ctx.set(session_id)
