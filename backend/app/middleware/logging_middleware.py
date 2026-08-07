"""
Request logging middleware.

Logs every incoming request/response with method, path, status, and latency.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import get_logger

log = get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        log.info(
            "{method} {path} → {status} ({ms}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=elapsed,
        )
        return response
