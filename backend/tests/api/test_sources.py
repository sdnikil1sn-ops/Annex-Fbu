"""API tests for the v1 sources endpoints (Phase 14 + Phase 19)."""

from __future__ import annotations

from app.application.services.source_service import SourceService
from app.infrastructure.repositories.mock_source_repository import MockSourceRepository
from app.main import create_app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _client(settings, token_verifier=None, user_service=None) -> TestClient:
    """A client with the mock-backed source service wired in.

    With ``token_verifier``/``user_service`` supplied the rate endpoint
    and authenticated reads work; without them only public reads do.
    """
    repository = MockSourceRepository()
    app = create_app(
        settings,
        source_service=SourceService(repository),
        token_verifier=token_verifier,
        user_service=user_service,
    )
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
    # Phase 19: an anonymous read still carries the community aggregate.
    assert data["community"] == {"count": 0, "average": None, "my_rating": None}


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


def test_rate_requires_token(settings, token_verifier, user_service) -> None:
    """A missing bearer token yields the 401 envelope."""
    client = _client(settings, token_verifier, user_service)
    response = client.post(
        "/api/v1/sources/reuters.com/rate", json={"rating": 5}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_rate_updates_community_signal(
    settings, token_verifier, user_service
) -> None:
    """Rating returns the updated profile with community count/average."""
    client = _client(settings, token_verifier, user_service)
    response = client.post(
        "/api/v1/sources/reuters.com/rate",
        headers=_headers(),
        json={"rating": 5},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["community"]["count"] == 1
    assert data["community"]["average"] == 5.0
    assert data["community"]["my_rating"] == 5


def test_rate_is_one_voice_per_user(
    settings, token_verifier, user_service
) -> None:
    """Re-rating replaces the caller's rating instead of adding one."""
    client = _client(settings, token_verifier, user_service)
    first = client.post(
        "/api/v1/sources/reuters.com/rate",
        headers=_headers(),
        json={"rating": 5},
    )
    second = client.post(
        "/api/v1/sources/reuters.com/rate",
        headers=_headers(),
        json={"rating": 2},
    )
    assert first.json()["data"]["community"]["count"] == 1
    data = second.json()["data"]
    assert data["community"]["count"] == 1
    assert data["community"]["average"] == 2.0
    assert data["community"]["my_rating"] == 2


def test_rate_validates_range(settings, token_verifier, user_service) -> None:
    """A rating outside 1..5 is a validation error."""
    client = _client(settings, token_verifier, user_service)
    response = client.post(
        "/api/v1/sources/reuters.com/rate",
        headers=_headers(),
        json={"rating": 7},
    )
    assert response.status_code == 422


def test_rate_unknown_source_returns_404(
    settings, token_verifier, user_service
) -> None:
    """Rating an unknown domain answers 404 with the source code."""
    client = _client(settings, token_verifier, user_service)
    response = client.post(
        "/api/v1/sources/unknown-domain.xyz/rate",
        headers=_headers(),
        json={"rating": 4},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "source.not_found"


def test_authenticated_read_includes_my_rating(
    settings, token_verifier, user_service
) -> None:
    """A token on the profile read surfaces the caller's own rating."""
    client = _client(settings, token_verifier, user_service)
    client.post(
        "/api/v1/sources/reuters.com/rate",
        headers=_headers(),
        json={"rating": 4},
    )
    response = client.get(
        "/api/v1/sources/reuters.com", headers=_headers()
    )
    assert response.status_code == 200
    community = response.json()["data"]["community"]
    assert community["count"] == 1
    assert community["average"] == 4.0
    assert community["my_rating"] == 4

    # Anonymous reads do not leak the caller's rating.
    anonymous = client.get("/api/v1/sources/reuters.com")
    assert anonymous.json()["data"]["community"]["my_rating"] is None


def test_sources_not_configured_returns_503(client: TestClient) -> None:
    """Without a wired source service, the endpoints answer 503."""
    response = client.get("/api/v1/sources/reuters.com")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "sources.not_configured"
