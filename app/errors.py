"""Structured API errors and FastAPI exception handlers."""
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


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

