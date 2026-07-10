from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Bind request_id so all logs within this request include it
        structlog.contextvars.bind_contextvars(request_id=request_id)

        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            log.error("http.error", error=str(exc))
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            structlog.contextvars.clear_contextvars()

        log.info(
            "http.response",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
