"""API tests for the v1 sources endpoints (Phase 14)."""

from __future__ import annotations

from app.application.services.source_service import SourceService
from app.infrastructure.repositories.mock_source_repository import MockSourceRepository
from app.main import create_app
from fastapi.testclient import TestClient


def _client(settings: TestClient) -> TestClient:
    """A client with the mock-backed source service wired in."""
    app = create_app(settings, source_service=SourceService(MockSourceRepository()))
    return TestClient(app, raise_server_exceptions=False)


def test_get_source_profile(settings) -> None:
    """A known domain returns its profile with the latest credibility score."""
    client = _client(settings)
    response = client.get("/api/v1/sources/reuters.com")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["domain"] == "reuters.com"
    assert data["name"] == "Reuters"
    assert data["score"] == 0.92
    assert data["signals"]["fact_checking"] == "strong"
    assert data["category"] == "news"
    assert data["model"] == "seed-v1"


def test_get_missing_source_returns_404(settings) -> None:
    """An unknown domain yields a 404 envelope."""
    client = _client(settings)
    response = client.get("/api/v1/sources/unknown-domain.xyz")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "source.not_found"


def test_search_matches_domain_and_name(settings) -> None:
    """Search matches partial domains and names case-insensitively."""
    client = _client(settings)

    by_domain = client.get("/api/v1/sources/search", params={"q": "reuter"})
    assert by_domain.status_code == 200
    domains = [item["domain"] for item in by_domain.json()["data"]]
    assert domains == ["reuters.com"]

    by_name = client.get("/api/v1/sources/search", params={"q": "conspiracy"})
    assert by_name.status_code == 200
    domains = [item["domain"] for item in by_name.json()["data"]]
    assert domains == ["conspiracy-news.net"]


def test_search_returns_empty_for_unknown(settings) -> None:
    """No matches yields an empty list, not an error."""
    client = _client(settings)
    response = client.get("/api/v1/sources/search", params={"q": "zzzz"})
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_search_requires_min_query_length(settings) -> None:
    """A too-short query is a validation error."""
    client = _client(settings)
    response = client.get("/api/v1/sources/search", params={"q": "a"})
    assert response.status_code == 422


def test_sources_not_configured_returns_503(client: TestClient) -> None:
    """Without a wired source service, the endpoints answer 503."""
    response = client.get("/api/v1/sources/reuters.com")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "sources.not_configured"
