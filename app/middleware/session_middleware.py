from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        session_id = request.headers.get("X-Adventure-Session-ID")

        if not session_id:
            session_id = request.cookies.get("adventure_session_id")

        if not session_id:
            session_id = None

        response = await call_next(request)

        if session_id:
            response.headers["X-Adventure-Session-ID"] = session_id

        return response
