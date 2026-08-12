"""Integration tests: PostgresAnalysisRepository against a real database.

Gated on TEST_DATABASE_URL; the schema is applied from the versioned
migrations on every run (helpers.apply_migrations).
"""

from __future__ import annotations

import os
from dataclasses import replace
from uuid import uuid4

import pytest
from app.application.ports.repositories import AnalysisRepository
from app.domain.analysis import Analysis, AnalysisInputType, AnalysisStatus
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> AnalysisRepository:
    """A fresh-schema Postgres repository per test."""
    apply_migrations(TEST_DSN)
    return PostgresAnalysisRepository(TEST_DSN)


def test_create_and_get(repository: AnalysisRepository) -> None:
    """A created analysis round-trips through the database."""
    analysis = Analysis(input_type=AnalysisInputType.URL, user_id=None)
    created = repository.create(analysis)
    fetched = repository.get(created.analysis_id)
    assert fetched is not None
    assert fetched.analysis_id == created.analysis_id
    assert fetched.input_type is AnalysisInputType.URL
    assert fetched.status is AnalysisStatus.PENDING
    assert fetched.created_at == created.created_at


def test_get_missing_returns_none(repository: AnalysisRepository) -> None:
    """An unknown ID yields None, not an error."""
    assert repository.get(uuid4()) is None


def test_update_status_persists(repository: AnalysisRepository) -> None:
    """State transitions are persisted and reloadable."""
    analysis = repository.create(Analysis())
    processing = analysis.transition_to(AnalysisStatus.PROCESSING)
    repository.update_status(processing)
    completed = processing.transition_to(AnalysisStatus.COMPLETED)
    repository.update_status(completed)

    fetched = repository.get(analysis.analysis_id)
    assert fetched is not None
    assert fetched.status is AnalysisStatus.COMPLETED
    assert fetched.completed_at is not None


def test_report_round_trips(repository: AnalysisRepository) -> None:
    """The report JSONB column survives a write + read cycle."""
    analysis = repository.create(Analysis())
    completed = analysis.transition_to(AnalysisStatus.COMPLETED)
    repository.update_status(
        replace(completed, report={"summary": "s", "claims": [{"text": "c"}]})
    )

    fetched = repository.get(analysis.analysis_id)
    assert fetched is not None
    assert fetched.report == {"summary": "s", "claims": [{"text": "c"}]}


def test_content_round_trips(repository: AnalysisRepository) -> None:
    """The content column survives a write + read cycle (worker reprocessing)."""
    analysis = repository.create(Analysis(content="untrusted text"))

    fetched = repository.get(analysis.analysis_id)
    assert fetched is not None
    assert fetched.content == "untrusted text"


def test_list_by_user_orders_newest_first(repository: AnalysisRepository) -> None:
    """A user's analyses come back newest-first with pagination support."""
    owner = uuid4()
    other = uuid4()
    create_user(TEST_DSN, owner)
    create_user(TEST_DSN, other)
    first = repository.create(Analysis(user_id=owner))
    second = repository.create(Analysis(user_id=owner))
    repository.create(Analysis(user_id=other))  # another user's row

    listed = repository.list_by_user(owner)
    ids = [item.analysis_id for item in listed]
    assert ids == [second.analysis_id, first.analysis_id]

    page = repository.list_by_user(owner, limit=1, cursor=(second.created_at, second.analysis_id))
    assert [item.analysis_id for item in page] == [first.analysis_id]


def test_delete_removes_row(repository: AnalysisRepository) -> None:
    """Deleting removes the row and reports success."""
    analysis = repository.create(Analysis())
    assert repository.delete(analysis.analysis_id) is True
    assert repository.get(analysis.analysis_id) is None
    assert repository.delete(analysis.analysis_id) is False
