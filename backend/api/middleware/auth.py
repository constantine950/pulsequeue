
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import settings

EXEMPT_PATHS = {"/health", "/ready", "/", "/docs", "/redoc", "/openapi.json"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Auth disabled
        if not settings.api_key:
            return await call_next(request)

        # Exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Check header
        key = request.headers.get(settings.api_key_header, "")
        if key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
                headers={
                    "WWW-Authenticate": f'ApiKey header="{settings.api_key_header}"'},
            )

        return await call_next(request)
