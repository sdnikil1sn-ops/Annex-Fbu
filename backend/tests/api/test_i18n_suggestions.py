"""API tests: the community translation suggestion endpoints (Phase 18).

Submissions require a token; the review queue and reviews require the
``moderator`` (or ``admin``) role; the missing-keys listing is public.
The fixtures wire the in-memory suggestion + i18n repositories; the
plain ``client`` fixture exercises the 503 path.
"""

from __future__ import annotations

from uuid import uuid4

from app.application.ports.auth import VerifiedIdentity
from app.application.services.i18n_service import I18nService
from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.domain.user import User
from app.infrastructure.repositories.mock_i18n_repository import MockI18nRepository
from app.infrastructure.repositories.mock_translation_suggestion_repository import (
    MockTranslationSuggestionRepository,
)
from app.main import create_app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _moderator_headers() -> dict[str, str]:
    return {"Authorization": "Bearer moderator-token"}


def _build(settings, token_verifier, user_service):
    """An app with mock auth + mock-backed suggestion/i18n services."""
    repository = MockTranslationSuggestionRepository()
    repository.seed_translation("en", "common", "cancel", "Cancel")
    repository.seed_translation("en", "common", "save", "Save")
    repository.seed_translation("pt", "common", "cancel", "Cancelar")
    i18n = MockI18nRepository.seeded()
    suggestion_service = TranslationSuggestionService(repository, i18n)
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        translation_suggestion_service=suggestion_service,
        i18n_service=I18nService(i18n, default_locale="en"),
    )
    return app, repository, i18n


def _add_moderator(token_verifier, user_service, uid) -> None:
    """Register a moderator identity + role under ``moderator-token``."""
    from app.infrastructure.repositories.mock_user_repository import MockUserRepository

    token_verifier._identities["moderator-token"] = VerifiedIdentity(  # type: ignore[attr-defined]
        uid=uid, email="mod@example.com", display_name="Moderator"
    )
    mock_repo: MockUserRepository = user_service._repository  # type: ignore[attr-defined]
    mock_repo.seed_user(User(id=uid, email="mod@example.com", role="moderator"))


def test_missing_requires_no_token(settings, token_verifier, user_service) -> None:
    """The missing-keys listing is public like the bundle endpoints."""
    app, repository, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/i18n/suggestions/missing?locale=pt")
    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["key"] for item in data] == ["save"]
    assert data[0]["english"] == "Save"
    assert response.json()["meta"]["count"] == 1


def test_submit_requires_token(settings, token_verifier, user_service) -> None:
    """A missing bearer token yields the 401 envelope."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/i18n/suggestions",
            json={"locale": "pt", "namespace": "common", "key": "save", "value": "Salvar"},
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_submit_creates_pending_suggestion(
    settings, token_verifier, user_service
) -> None:
    """Submitting a translation proposal returns it as pending."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/i18n/suggestions",
            headers=_headers(),
            json={"locale": "pt", "namespace": "common", "key": "save", "value": "Salvar"},
        )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["locale"] == "pt"
    assert data["status"] == "pending"
    assert data["value"] == "Salvar"
    assert data["suggested_by"]


def test_submit_unknown_locale_returns_404(settings, token_verifier, user_service) -> None:
    """A locale outside the enabled set answers 404 with the i18n code."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/i18n/suggestions",
            headers=_headers(),
            json={"locale": "zz", "namespace": "common", "key": "save", "value": "X"},
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "i18n.locale_not_found"


def test_submit_is_idempotent_per_user_key(settings, token_verifier, user_service) -> None:
    """Re-submitting the same key updates the contributor's pending row."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post(
            "/api/v1/i18n/suggestions",
            headers=_headers(),
            json={"locale": "pt", "namespace": "common", "key": "save", "value": "Salvar"},
        )
        second = client.post(
            "/api/v1/i18n/suggestions",
            headers=_headers(),
            json={"locale": "pt", "namespace": "common", "key": "save", "value": "Gravar"},
        )
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["data"]["value"] == "Gravar"


def test_list_own_suggestions(settings, token_verifier, user_service) -> None:
    """The caller sees their own suggestions, newest first."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(
            "/api/v1/i18n/suggestions",
            headers=_headers(),
            json={"locale": "pt", "namespace": "common", "key": "save", "value": "Salvar"},
        )
        listing = client.get("/api/v1/i18n/suggestions", headers=_headers())
    assert listing.status_code == 200
    data = listing.json()["data"]
    assert len(data) == 1
    assert data[0]["key"] == "save"


def test_pending_queue_requires_moderator(
    settings, token_verifier, user_service
) -> None:
    """The review queue is moderator-only (403 for plain users)."""
    app, _, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        denied = client.get("/api/v1/i18n/suggestions/pending", headers=_headers())
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "auth.insufficient_role"


def test_review_requires_moderator(settings, token_verifier, user_service) -> None:
    """Reviews are moderator-only; a plain user gets 403."""
    app, repository, _ = _build(settings, token_verifier, user_service)
    suggestion = repository.seed_suggestion(
        "pt", "common", "save", "Salvar", uuid4()
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/i18n/suggestions/{suggestion.id}/review",
            headers=_headers(),
            json={"approved": True},
        )
    assert response.status_code == 403


def test_review_approves_and_publishes(settings, token_verifier, user_service) -> None:
    """A moderator approving publishes the value into the live bundles."""
    app, repository, i18n = _build(settings, token_verifier, user_service)
    _add_moderator(token_verifier, user_service, uuid4())
    suggestion = repository.seed_suggestion(
        "pt", "common", "save", "Salvar", uuid4()
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        reviewed = client.post(
            f"/api/v1/i18n/suggestions/{suggestion.id}/review",
            headers=_moderator_headers(),
            json={"approved": True},
        )
        bundle = client.get("/api/v1/i18n/bundles/pt")
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["status"] == "approved"

    # The published value is served in the live bundle.
    entries = bundle.json()["data"]["entries"]
    assert entries["common.save"] == {"value": "Salvar", "plural": "none"}
    assert any(
        entry.namespace == "common"
        and entry.key == "save"
        and entry.value == "Salvar"
        for entry in i18n.translations_for("pt")
    )


def test_review_rejects(settings, token_verifier, user_service) -> None:
    """A moderator rejecting marks the suggestion rejected."""
    app, repository, _ = _build(settings, token_verifier, user_service)
    _add_moderator(token_verifier, user_service, uuid4())
    suggestion = repository.seed_suggestion(
        "pt", "common", "save", "Salvar", uuid4()
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/i18n/suggestions/{suggestion.id}/review",
            headers=_moderator_headers(),
            json={"approved": False},
        )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"


def test_review_unknown_suggestion_returns_404(
    settings, token_verifier, user_service
) -> None:
    """An unknown suggestion id answers 404 with the suggestion code."""
    app, _, _ = _build(settings, token_verifier, user_service)
    _add_moderator(token_verifier, user_service, uuid4())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/i18n/suggestions/{uuid4()}/review",
            headers=_moderator_headers(),
            json={"approved": True},
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "i18n.suggestion_not_found"


def test_suggestions_not_configured_returns_503(authed_client: TestClient) -> None:
    """Without a wired suggestion service the endpoints answer 503."""
    response = authed_client.get("/api/v1/i18n/suggestions/missing?locale=pt")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "i18n.suggestions_not_configured"
