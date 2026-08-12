"""Rate-limit ASGI middleware (Phase 7).

Applies the fixed-window limiter to every HTTP request, keyed on the client
address (first hop of ``X-Forwarded-For`` when present — the production
proxy injects it) and the endpoint scope (analysis vs default). Responses
use the standard error envelope and therefore carry the request ID once the
outer request-ID middleware appends it.
"""

from __future__ import annotations

import json

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import request_id_var
from app.infrastructure.rate_limit.limiter import RateLimiter

ANALYSIS_PATH_PREFIX = "/api/v1/analysis"
SCOPE_DEFAULT = "default"
SCOPE_ANALYSIS = "analysis"


class RateLimitMiddleware:
    """Reject requests exceeding the scope limit with a 429 envelope."""

    def __init__(self, app: ASGIApp, limiter: RateLimiter) -> None:
        self.app = app
        self._limiter = limiter

    @staticmethod
    def _client_key(request: Request) -> str:
        """Identify the caller: first proxy hop, else the peer address."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        scope_name = SCOPE_ANALYSIS if path.startswith(ANALYSIS_PATH_PREFIX) else SCOPE_DEFAULT
        client_key = self._client_key(request)
        if not self._limiter.allow(scope_name, client_key):
            body = json.dumps(
                {
                    "error": {
                        "code": "rate_limit.exceeded",
                        "message": "Rate limit exceeded. Try again shortly.",
                        "request_id": request_id_var.get(),
                        "details": {"scope": scope_name},
                    }
                }
            ).encode()
            response = Response(body, status_code=429, media_type="application/json")
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
