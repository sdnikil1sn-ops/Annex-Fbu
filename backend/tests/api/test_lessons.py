"""API tests for the v1 lessons endpoints (Phase 15)."""

from __future__ import annotations

from uuid import uuid4

from app.application.services.education_service import EducationService
from app.domain.user import User
from app.infrastructure.repositories.mock_i18n_repository import MockI18nRepository
from app.infrastructure.repositories.mock_lesson_repository import MockLessonRepository
from app.main import create_app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _build(settings, token_verifier, user_service, *, locale: str = "en"):
    """An app with mock auth + the mock-backed education service."""
    if locale != "en":
        mock_repo = user_service._repository  # type: ignore[attr-defined]
        identity = token_verifier._identities["test-token"]  # type: ignore[attr-defined]
        mock_repo.seed_user(
            User(
                id=identity.uid,
                email=identity.email,
                locale=locale,
            )
        )
    education_service = EducationService(
        MockLessonRepository(),
        MockI18nRepository.seeded(),
        default_locale="en",
    )
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        education_service=education_service,
    )
    return app


def test_list_lessons_requires_token(settings, token_verifier, user_service) -> None:
    """A missing bearer token yields a 401 envelope."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/lessons")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_list_lessons_returns_english_curriculum(
    settings, token_verifier, user_service
) -> None:
    """The default-locale user gets the English curriculum in order."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/lessons", headers=_headers())
    assert response.status_code == 200
    lessons = response.json()["data"]
    assert [lesson["slug"] for lesson in lessons] == [
        "spotting-misinformation",
        "understanding-credibility-scores",
    ]
    first = lessons[0]
    assert first["title"] == "Spotting Misinformation"
    assert first["summary"].startswith("Learn to recognize")
    assert first["completed"] is False
    assert "sections" not in first  # list payload is metadata only


def test_list_lessons_uses_user_locale(settings, token_verifier, user_service) -> None:
    """A pt user gets the pt variant where it exists."""
    app = _build(settings, token_verifier, user_service, locale="pt")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/lessons", headers=_headers())
    assert response.status_code == 200
    lessons = response.json()["data"]
    assert lessons[0]["title"] == "Como Detectar Desinformação"
    # The second lesson has no pt content -> falls back to en.
    assert lessons[1]["title"] == "Understanding Credibility Scores"


def test_get_lesson_returns_content_and_sections(
    settings, token_verifier, user_service
) -> None:
    """Detail payload carries sections and the resolved locale."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get("/api/v1/lessons", headers=_headers())
        lesson_id = listing.json()["data"][0]["id"]
        response = client.get(f"/api/v1/lessons/{lesson_id}", headers=_headers())
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["locale"] == "en"
    assert payload["sections"]
    assert payload["sections"][0]["heading"] == "Why misinformation spreads"
    assert payload["sections"][0]["bullets"]


def test_get_lesson_by_slug(settings, token_verifier, user_service) -> None:
    """Lessons are addressable by their stable slug too."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/lessons/spotting-misinformation", headers=_headers()
        )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["slug"] == "spotting-misinformation"
    assert payload["locale"] == "en"
    assert payload["sections"]


def test_complete_lesson_by_slug(settings, token_verifier, user_service) -> None:
    """Completion accepts the slug reference too."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/lessons/spotting-misinformation/complete", headers=_headers()
        )
    assert response.status_code == 200
    assert response.json()["data"]["completed_at"]


def test_get_missing_lesson_is_404(settings, token_verifier, user_service) -> None:
    """An unknown lesson id or slug yields a 404 envelope."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        by_id = client.get(f"/api/v1/lessons/{uuid4()}", headers=_headers())
        by_slug = client.get("/api/v1/lessons/no-such-lesson", headers=_headers())
    assert by_id.status_code == 404
    assert by_slug.status_code == 404
    assert by_slug.json()["error"]["code"] == "lesson.not_found"


def test_complete_lesson_is_idempotent(
    settings, token_verifier, user_service
) -> None:
    """Completing twice keeps the first timestamp; progress surfaces."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get("/api/v1/lessons", headers=_headers())
        lesson_id = listing.json()["data"][0]["id"]

        first = client.post(
            f"/api/v1/lessons/{lesson_id}/complete", headers=_headers()
        )
        second = client.post(
            f"/api/v1/lessons/{lesson_id}/complete", headers=_headers()
        )
        refreshed = client.get("/api/v1/lessons", headers=_headers())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["completed_at"] == second.json()["data"]["completed_at"]
    assert refreshed.json()["data"][0]["completed"] is True


def test_complete_missing_lesson_is_404(
    settings, token_verifier, user_service
) -> None:
    """Completing an unknown lesson yields a 404 envelope."""
    app = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/lessons/{uuid4()}/complete", headers=_headers()
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lesson.not_found"


def test_lessons_not_configured_returns_503(authed_client: TestClient) -> None:
    """Without a wired education service, the endpoints answer 503."""
    response = authed_client.get("/api/v1/lessons", headers=_headers())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "education.not_configured"
