"""API tests for the error envelope contract."""

from collections.abc import Callable

from app.api.errors import AppError, register_exception_handlers
from app.core.logging import configure_logging
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app_with(handler: Callable[[], object]) -> FastAPI:
    """Build a minimal application with one route and the error handlers."""
    configure_logging("WARNING")
    app = FastAPI()
    app.add_api_route("/route", handler, methods=["GET"])
    register_exception_handlers(app)
    return app


def test_unknown_route_returns_envelope(client: TestClient) -> None:
    """404s are normalized into the error envelope."""
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http.404"
    assert "request_id" in error


def test_validation_error_returns_envelope() -> None:
    """Malformed input produces a structured validation error."""

    def endpoint(value: int) -> dict[str, int]:
        return {"value": value}

    app = _app_with(endpoint)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/route?value=not-an-int")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation.invalid_input"
    assert error["details"]["errors"]


def test_validation_error_does_not_echo_input() -> None:
    """Submitted values must never be echoed back in a 422 response."""

    def endpoint(value: int) -> dict[str, int]:
        return {"value": value}

    app = _app_with(endpoint)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/route?value=super-secret-value")
    assert response.status_code == 422
    assert "super-secret-value" not in response.text
    for entry in response.json()["error"]["details"]["errors"]:
        assert "input" not in entry


def test_app_error_returns_envelope() -> None:
    """AppError maps code, message, and status into the envelope."""

    def endpoint() -> None:
        raise AppError("analysis.not_found", "Analysis not found.", status_code=404)

    app = _app_with(endpoint)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/route")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "analysis.not_found"
    assert error["message"] == "Analysis not found."


def test_unhandled_exception_does_not_leak_internals() -> None:
    """A 500 must never leak internal details to the client."""

    def endpoint() -> None:
        raise RuntimeError("secret internal detail")

    app = _app_with(endpoint)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/route")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal.error"
    assert "secret internal detail" not in error["message"]
    assert error["request_id"]  # correlation still available on 500s
