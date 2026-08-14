"""Unit tests for the SourceService (Phase 14 + Phase 19 feedback)."""

from __future__ import annotations

from uuid import uuid4

from app.application.services.source_service import SourceService
from app.domain.source import SourceFeedback
from app.infrastructure.repositories.mock_source_repository import MockSourceRepository


def _service() -> tuple[SourceService, MockSourceRepository]:
    repository = MockSourceRepository()
    return SourceService(repository), repository


def test_get_profile_returns_score_with_empty_community() -> None:
    """A profile without feedback carries count 0 and no average."""
    service, _ = _service()
    source = service.get_profile("reuters.com")

    assert source is not None and source.score == 0.92
    assert source.community is not None
    assert source.community.count == 0
    assert source.community.average is None
    assert source.community.my_rating is None


def test_rate_records_single_voice_per_user() -> None:
    """Rating updates the caller's own row; the aggregate reflects it."""
    service, _ = _service()
    user = uuid4()

    first = service.rate("reuters.com", user, 5)
    second = service.rate("reuters.com", user, 3)

    assert first is not None and second is not None
    assert first.community is not None and first.community.count == 1
    assert second.community is not None and second.community.count == 1
    assert second.community.average == 3.0
    assert second.community.my_rating == 3


def test_rate_aggregates_across_users() -> None:
    """Distinct users each contribute one rating to the average."""
    service, _ = _service()
    alice, bob, carol = uuid4(), uuid4(), uuid4()

    service.rate("reuters.com", alice, 5)
    service.rate("reuters.com", bob, 4)
    rated = service.rate("reuters.com", carol, 3)

    assert rated is not None and rated.community is not None
    assert rated.community.count == 3
    assert rated.community.average == 4.0


def test_rate_unknown_source_is_none() -> None:
    """An unknown domain yields None, not an error."""
    service, _ = _service()
    assert service.rate("no-such-domain.example", uuid4(), 4) is None


def test_get_profile_includes_my_rating_for_caller() -> None:
    """Reading a profile for an authenticated user carries their rating."""
    service, repository = _service()
    user = uuid4()
    repository.seed_feedback("reuters.com", user, 2)

    source = service.get_profile("reuters.com", user_id=user)

    assert source is not None and source.community is not None
    assert source.community.count == 1
    assert source.community.my_rating == 2


def test_search_attaches_community() -> None:
    """Search results carry the community aggregate like the profile."""
    service, repository = _service()
    user = uuid4()
    repository.seed_feedback("conspiracy-news.net", user, 1)

    results = service.search("conspiracy")

    assert len(results) == 1
    community: SourceFeedback | None = results[0].community
    assert community is not None
    assert community.count == 1
    assert community.average == 1.0
