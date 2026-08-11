"""Shared pytest fixtures for the backend test suite."""

from uuid import uuid4

import pytest
from app.application.ports.auth import VerifiedIdentity
from app.application.services.user_service import UserService
from app.core.config import Settings
from app.infrastructure.auth.mock_token_verifier import MockTokenVerifier
from app.infrastructure.repositories.mock_user_repository import MockUserRepository
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture()
def settings() -> Settings:
    """Deterministic test settings (no .env file, quiet logs)."""
    return Settings(_env_file=None, app_env="test", log_level="WARNING")


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """TestClient bound to an application built from test settings.

    ``raise_server_exceptions=False`` lets tests assert on 500 envelopes
    instead of re-raising server errors.
    """
    app = create_app(settings)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def verified_identity() -> VerifiedIdentity:
    """A verified identity for a test user."""
    return VerifiedIdentity(uid=uuid4(), email="alice@example.com", display_name="Alice")


@pytest.fixture()
def token_verifier(verified_identity: VerifiedIdentity) -> MockTokenVerifier:
    """A mock verifier that accepts the fixed test token."""
    return MockTokenVerifier({"test-token": verified_identity})


@pytest.fixture()
def user_service() -> UserService:
    """A user service backed by an in-memory repository."""
    return UserService(MockUserRepository())


@pytest.fixture()
def authed_client(
    settings: Settings,
    token_verifier: MockTokenVerifier,
    user_service: UserService,
) -> TestClient:
    """A client with mock authentication fully wired."""
    app = create_app(settings, token_verifier=token_verifier, user_service=user_service)
    return TestClient(app, raise_server_exceptions=False)
