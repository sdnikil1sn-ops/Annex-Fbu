"""Integration tests: PostgresSourceRepository against a real database.

The sources are seeded by migration 20260812000004, which is applied by
helpers.apply_migrations on every run.
"""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from app.application.ports.repositories import SourceRepository
from app.infrastructure.repositories.source_repository import PostgresSourceRepository

from tests.integration.helpers import apply_migrations

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> SourceRepository:
    """A fresh-schema Postgres source repository per test (seeded)."""
    apply_migrations(TEST_DSN)
    return PostgresSourceRepository(TEST_DSN)


def test_get_by_domain_returns_profile_with_score(repository: SourceRepository) -> None:
    """The seed migration populates profiles readable via the repository."""
    source = repository.get_by_domain("reuters.com")
    assert source is not None
    assert isinstance(source.id, UUID)
    assert source.name == "Reuters"
    assert source.score == 0.92
    assert source.signals["fact_checking"] == "strong"
    assert source.model == "seed-v1"
    assert source.computed_at is not None


def test_get_missing_domain_returns_none(repository: SourceRepository) -> None:
    """An unknown domain yields None, not an error."""
    assert repository.get_by_domain("nonexistent.example") is None


def test_search_matches_domain_and_name(repository: SourceRepository) -> None:
    """Search is a case-insensitive substring match on domain or name."""
    by_domain = repository.search("reuter")
    assert [s.domain for s in by_domain] == ["reuters.com"]

    by_name = repository.search("snopes")
    assert [s.domain for s in by_name] == ["snopes.com"]

    empty = repository.search("zzzzzz")
    assert empty == []


def test_search_respects_limit(repository: SourceRepository) -> None:
    """The limit caps the number of returned sources."""
    results = repository.search(".", limit=2)
    assert len(results) <= 2
