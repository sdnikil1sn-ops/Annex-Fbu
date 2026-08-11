"""Request-ID middleware.

Assigns a fresh UUID per HTTP request, exposes it through the logging
context variable, and returns it in the ``X-Request-ID`` response header.

Client-supplied request IDs are never trusted (log-forging prevention):
the service always generates its own ID and ignores any incoming value.
"""

import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var

# Response header that carries the request ID back to the client.
RequestIdHeader = "X-REQUEST-ID"


class RequestIdMiddleware:
    """ASGI middleware assigning a request ID to every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Wrap the application with request-ID assignment for HTTP scopes."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)

        async def send_with_header(message: Message) -> None:
            """Append the request ID to the response start message."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((RequestIdHeader.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            request_id_var.reset(token)
