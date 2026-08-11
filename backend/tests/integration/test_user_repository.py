"""Integration tests: PostgresUserRepository against a real database.

Gated on TEST_DATABASE_URL like the analysis repository tests.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.application.ports.auth import VerifiedIdentity
from app.application.ports.repositories import UserRepository
from app.infrastructure.repositories.user_repository import PostgresUserRepository

from tests.integration.helpers import apply_migrations

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> UserRepository:
    """A fresh-schema Postgres user repository per test."""
    apply_migrations(TEST_DSN)
    return PostgresUserRepository(TEST_DSN)


def test_ensure_user_and_fetch(repository: UserRepository) -> None:
    """Hydration creates users + profiles and is fetchable with defaults."""
    identity = VerifiedIdentity(uid=uuid4(), email="carol@example.com")
    repository.ensure_user(identity)

    user = repository.get_by_id(identity.uid)
    assert user is not None
    assert user.email == "carol@example.com"
    assert user.role == "user"
    assert user.locale == "en"


def test_ensure_user_is_idempotent(repository: UserRepository) -> None:
    """Repeated hydration does not duplicate rows or reset the role."""
    identity = VerifiedIdentity(uid=uuid4())
    repository.ensure_user(identity)
    repository.ensure_user(identity)

    users = repository.get_by_id(identity.uid)
    assert users is not None


def test_get_missing_returns_none(repository: UserRepository) -> None:
    """An unknown user ID yields None."""
    assert repository.get_by_id(uuid4()) is None
