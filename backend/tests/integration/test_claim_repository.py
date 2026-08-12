"""Integration tests: PostgresClaimRepository against a real database.

Gated on TEST_DATABASE_URL; the schema is applied from the versioned
migrations on every run (helpers.apply_migrations).
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from app.application.ports.repositories import ClaimRepository
from app.domain.analysis import Analysis, AnalysisInputType
from app.domain.claim import Claim, Evidence
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.repositories.claim_repository import PostgresClaimRepository

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> ClaimRepository:
    """A fresh-schema Postgres claim repository per test."""
    apply_migrations(TEST_DSN)
    return PostgresClaimRepository(TEST_DSN)


@pytest.fixture()
def analysis_id() -> UUID:
    """An owned analysis row for claims to reference."""
    owner = uuid4()
    create_user(TEST_DSN, owner)
    analysis = PostgresAnalysisRepository(TEST_DSN).create(
        Analysis(input_type=AnalysisInputType.TEXT, user_id=owner, content="x")
    )
    return analysis.analysis_id


def test_save_and_get_round_trip(repository: ClaimRepository, analysis_id: UUID) -> None:
    """A claim persists with its verdict and evidence and reads back intact."""
    claim = Claim(
        analysis_id=analysis_id,
        claim_index=0,
        text="The sky is blue.",
        normalized_text="the sky is blue.",
        verdict="verifiable",
        confidence=0.9,
        rationale="Well-sourced.",
        model="openai:gpt-4o-mini",
        evidence=(
            Evidence(kind="link", url="https://example.com/a", relevance=0.9),
            Evidence(kind="quote", quote="The sky is blue per NWS."),
        ),
    )
    saved = repository.save(claim)

    fetched = repository.get(saved.id)
    assert fetched is not None
    assert fetched.analysis_id == analysis_id
    assert fetched.text == claim.text
    assert fetched.normalized_text == claim.normalized_text
    assert fetched.verdict == "verifiable"
    assert fetched.confidence == 0.9
    assert fetched.rationale == "Well-sourced."
    assert fetched.model == "openai:gpt-4o-mini"
    assert len(fetched.evidence) == 2
    assert fetched.evidence[0].url == "https://example.com/a"
    assert fetched.evidence[1].kind == "quote"


def test_get_missing_returns_none(repository: ClaimRepository) -> None:
    """An unknown claim id yields None, not an error."""
    assert repository.get(uuid4()) is None


def test_list_by_analysis_orders_by_claim_index(
    repository: ClaimRepository, analysis_id: UUID
) -> None:
    """Claims for one analysis come back in claim order."""
    first = repository.save(
        Claim(analysis_id=analysis_id, claim_index=0, text="First", verdict="verifiable")
    )
    second = repository.save(
        Claim(analysis_id=analysis_id, claim_index=1, text="Second", verdict="verifiable")
    )

    listed = repository.list_by_analysis(analysis_id)
    assert [claim.id for claim in listed] == [first.id, second.id]
    assert listed[0].claim_index == 0 and listed[1].claim_index == 1


def test_list_by_analysis_empty(repository: ClaimRepository) -> None:
    """An analysis without claims yields an empty list."""
    assert repository.list_by_analysis(uuid4()) == []
