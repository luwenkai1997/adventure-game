"""Structured API errors and FastAPI exception handlers."""
import functools
import logging
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody


class AppError(Exception):
    """Application-level error with stable code and HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=exc.code, message=exc.message, detail=exc.detail)
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppError):
        return await app_error_handler(request, exc)
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    body = ErrorResponse(
        error=ErrorBody(
            code="internal_error",
            message="服务器内部错误",
            detail=str(exc) if exc else None,
        )
    )
    return JSONResponse(status_code=500, content=body.model_dump())


def route_handler(operation: str = "操作"):
    """Decorator for route handlers that catches exceptions and returns JSON error responses.
    
    Usage:
        @router.get("/api/endpoint")
        @route_handler("描述该操作")
        async def my_endpoint():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppError:
                raise
            except Exception as e:
                logger.error(f"{operation}失败", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"error": f"{operation}失败: {str(e)}"}
                )
        return wrapper
    return decorator

