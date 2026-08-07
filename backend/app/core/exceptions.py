"""
Global exception handlers registered on the FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger("exceptions")


class AppException(Exception):
    """Base application exception with an HTTP status code and detail."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred.",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class AuthenticationError(AppException):
    def __init__(self, detail: str = "Authentication failed.") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Access denied.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class RateLimitError(AppException):
    def __init__(self, detail: str = "Rate limit exceeded. Try again later.") -> None:
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class LLMError(AppException):
    def __init__(self, detail: str = "Language model request failed.") -> None:
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation error.") -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        log.warning("AppException: status={status} detail={detail}", status=exc.status_code, detail=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled exception: {exc}", exc=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error."},
        )
