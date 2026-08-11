"""API tests for the system endpoints."""

from app import __version__
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    """The liveness probe returns the service identity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert data["environment"] == "test"


def test_health_ready(client: TestClient) -> None:
    """The readiness probe reports ok with an explicit dependency list."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["checks"] == []


def test_version_endpoint(client: TestClient) -> None:
    """The versioned metadata endpoint reports name and version."""
    response = client.get("/api/v1/meta/version")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "ANNEX API"
    assert data["version"] == __version__
    assert data["environment"] == "test"


def test_openapi_schema_advertises_v1(client: TestClient) -> None:
    """The generated OpenAPI schema must expose the versioned paths."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/meta/version" in paths
    assert "/health" in paths


def test_docs_ui_disabled_outside_debug(client: TestClient) -> None:
    """The interactive docs UI must not be served when debug is disabled."""
    response = client.get("/docs")
    assert response.status_code == 404


def test_preflight_carries_request_id(client: TestClient) -> None:
    """CORS preflight responses must include X-REQUEST-ID (outermost layer)."""
    response = client.options(
        "/api/v1/meta/version",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("X-REQUEST-ID") is not None
