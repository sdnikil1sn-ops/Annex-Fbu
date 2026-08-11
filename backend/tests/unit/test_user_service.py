"""Unit tests for the UserService against the mock repository."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.application.ports.auth import VerifiedIdentity
from app.application.services.user_service import UserService
from app.infrastructure.repositories.mock_user_repository import MockUserRepository


@pytest.fixture()
def service() -> UserService:
    return UserService(MockUserRepository())


def test_get_or_create_hydrates_default_user(service: UserService) -> None:
    """First authentication creates the user with default role and locale."""
    identity = VerifiedIdentity(uid=uuid4(), email="bob@example.com")
    user = service.get_or_create(identity)
    assert user.id == identity.uid
    assert user.email == "bob@example.com"
    assert user.role == "user"
    assert user.locale == "en"


def test_get_or_create_is_idempotent(service: UserService) -> None:
    """Repeated authentication does not duplicate or reset the user."""
    identity = VerifiedIdentity(uid=uuid4())
    first = service.get_or_create(identity)
    second = service.get_or_create(identity)
    assert first.id == second.id
    assert first.created_at == second.created_at


def test_get_missing_returns_none(service: UserService) -> None:
    """An unknown user ID yields None."""
    assert service.get(uuid4()) is None
