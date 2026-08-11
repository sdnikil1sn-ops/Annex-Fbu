"""API tests for the authenticated user endpoints."""

from uuid import UUID

from app.api.deps import require_roles
from app.core.config import Settings
from app.domain.user import User
from app.main import create_app
from fastapi import Depends
from fastapi.testclient import TestClient


def test_me_requires_token(authed_client: TestClient) -> None:
    """A missing bearer token yields a 401 envelope."""
    response = authed_client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_me_rejects_invalid_token(authed_client: TestClient) -> None:
    """An unverifiable token yields a 401 envelope."""
    response = authed_client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer bogus-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.invalid_token"


def test_me_returns_profile_for_valid_token(authed_client: TestClient, verified_identity) -> None:
    """A valid token returns the hydrated user profile."""
    response = authed_client.get("/api/v1/users/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(verified_identity.uid)
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert data["locale"] == "en"


def test_me_hydrates_user_on_first_login(authed_client: TestClient, user_service) -> None:
    """First successful authentication creates the user mirror."""
    response = authed_client.get("/api/v1/users/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    user_id = response.json()["data"]["id"]
    assert user_service.get(UUID(user_id)) is not None


def test_auth_not_configured_returns_503(settings: Settings) -> None:
    """Without a token verifier, protected routes answer 503."""
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/v1/users/me", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth.not_configured"


def test_require_roles_enforces_role(
    settings: Settings, token_verifier, verified_identity, user_service
) -> None:
    """require_roles rejects callers outside the permitted roles."""
    app = create_app(settings, token_verifier=token_verifier, user_service=user_service)

    moderator_dep = Depends(require_roles("moderator"))

    def moderator_only(user: User = moderator_dep) -> dict:
        return {"role": user.role}

    app.add_api_route("/moderator-only", moderator_only, methods=["GET"])

    with TestClient(app, raise_server_exceptions=False) as test_client:
        # Default role is "user" -> forbidden.
        denied = test_client.get("/moderator-only", headers={"Authorization": "Bearer test-token"})
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "auth.insufficient_role"

        # A seeded moderator is allowed.
        mock_repo = user_service._repository  # type: ignore[attr-defined]
        mock_repo.seed_user(
            User(
                id=verified_identity.uid,
                email=verified_identity.email,
                role="moderator",
            )
        )
        allowed = test_client.get("/moderator-only", headers={"Authorization": "Bearer test-token"})
        assert allowed.status_code == 200
        assert allowed.json()["role"] == "moderator"
