"""Integration tests: PostgresSourceRepository against a real database.

The sources are seeded by migration 20260812000004; the Phase 19
``source_feedback`` table comes from migration 20260815000001. All are
applied by helpers.apply_migrations on every run.
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from app.application.ports.repositories import SourceRepository
from app.infrastructure.repositories.source_repository import PostgresSourceRepository

from tests.integration.helpers import apply_migrations, create_user

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
    # Phase 19: feedback aggregate rides along, empty until rated.
    assert source.community is not None
    assert source.community.count == 0
    assert source.community.average is None


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


def test_rate_upserts_per_user(repository: SourceRepository) -> None:
    """Rating records one voice per user; re-rating updates the row."""
    alice, bob = uuid4(), uuid4()
    create_user(TEST_DSN, alice)
    create_user(TEST_DSN, bob)

    rated = repository.rate("reuters.com", alice, 5)
    assert rated is not None
    assert rated.community is not None and rated.community.count == 1
    assert rated.community.average == 5.0
    assert rated.community.my_rating == 5

    # A second user moves the average; alice re-rating keeps count stable.
    repository.rate("reuters.com", bob, 3)
    re_rated = repository.rate("reuters.com", alice, 4)
    assert re_rated is not None and re_rated.community is not None
    assert re_rated.community.count == 2
    assert re_rated.community.average == 3.5
    assert re_rated.community.my_rating == 4


def test_rate_unknown_source_is_none(repository: SourceRepository) -> None:
    """Rating an unknown domain returns None."""
    create_user(TEST_DSN, uuid4())
    assert repository.rate("nonexistent.example", uuid4(), 4) is None


def test_get_by_domain_with_user_attaches_my_rating(
    repository: SourceRepository,
) -> None:
    """Reading a profile for a user who rated it carries their rating."""
    user = uuid4()
    create_user(TEST_DSN, user)
    repository.rate("conspiracy-news.net", user, 1)

    source = repository.get_by_domain("conspiracy-news.net", user_id=user)
    assert source is not None and source.community is not None
    assert source.community.count == 1
    assert source.community.average == 1.0
    assert source.community.my_rating == 1

    anonymous = repository.get_by_domain("conspiracy-news.net")
    assert anonymous is not None and anonymous.community is not None
    assert anonymous.community.count == 1
    assert anonymous.community.my_rating is None
