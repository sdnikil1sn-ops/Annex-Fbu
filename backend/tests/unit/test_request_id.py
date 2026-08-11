"""Tests for the request-ID middleware."""

import asyncio
from typing import Any

from app.core.request_id import RequestIdMiddleware
from fastapi.testclient import TestClient


def test_request_id_is_generated(client: TestClient) -> None:
    """Every response must carry a fresh X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    request_id = response.headers.get("X-REQUEST-ID")
    assert request_id is not None
    assert len(request_id) == 32  # uuid4().hex


def test_request_id_is_unique_per_request(client: TestClient) -> None:
    """Each request must receive a distinct request ID."""
    first = client.get("/health").headers.get("X-REQUEST-ID")
    second = client.get("/health").headers.get("X-REQUEST-ID")
    assert first != second


def test_client_supplied_request_id_is_not_trusted(client: TestClient) -> None:
    """A client-provided X-Request-ID must never be echoed back."""
    response = client.get("/health", headers={"X-REQUEST-ID": "forged-value"})
    assert response.headers.get("X-REQUEST-ID") != "forged-value"


def test_non_http_scope_passes_through_untouched() -> None:
    """Non-HTTP scopes (lifespan) must flow through without interception."""
    called: dict[str, bool] = {"inner": False}

    async def inner_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        called["inner"] = True

    middleware = RequestIdMiddleware(inner_app)  # type: ignore[arg-type]

    async def run() -> None:
        await middleware({"type": "lifespan"}, None, None)  # type: ignore[arg-type]

    asyncio.run(run())
    assert called["inner"] is True
