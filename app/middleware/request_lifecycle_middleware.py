import logging
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.request_context import (
    begin_file_io_cache,
    reset_file_io_cache,
    set_request_id,
)

logger = logging.getLogger(__name__)


class RequestLifecycleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(rid)
        cache_token = begin_file_io_cache()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            reset_file_io_cache(cache_token)
            set_request_id(None)
