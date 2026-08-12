"""Unit tests for the ClaimsService (Phase 14)."""

from __future__ import annotations

from uuid import uuid4

from app.application.ports.ai import ClaimAnalysis, ClaimItem, EvidenceItem
from app.application.services.claims_service import ClaimsService
from app.domain.analysis import Analysis, AnalysisInputType
from app.domain.claim import CLAIM_VERDICTS
from app.infrastructure.repositories.mock_claim_repository import MockClaimRepository


def _analysis(*, user_id=None) -> Analysis:
    return Analysis(
        input_type=AnalysisInputType.TEXT, user_id=user_id, content="Some text."
    )


def _result() -> ClaimAnalysis:
    return ClaimAnalysis(
        claims=[
            ClaimItem(
                text="The sky is blue.",
                verifiability=0.9,
                verdict="verifiable",
                rationale="Backed by multiple sources.",
                evidence=(
                    EvidenceItem(kind="link", url="https://example.com/a", relevance=0.9),
                    EvidenceItem(kind="quote", quote="The sky is blue per NWS."),
                ),
            ),
            ClaimItem(text="Gravity exists", verifiability=0.2),
        ],
        summary="Two claims checked.",
        model="openai:gpt-4o-mini",
    )


def test_save_persists_claims_with_verdicts_and_evidence() -> None:
    """Each claim becomes a persisted aggregate with verdict + evidence."""
    repository = MockClaimRepository()
    service = ClaimsService(repository)
    analysis = _analysis(user_id=uuid4())

    claims = service.save_from_analysis(analysis, _result())

    assert len(claims) == 2
    first, second = claims
    assert first.analysis_id == analysis.analysis_id
    assert first.user_id == analysis.user_id
    assert first.claim_index == 0
    assert first.verdict == "verifiable"
    assert first.confidence == 0.9
    assert first.model == "openai:gpt-4o-mini"
    assert first.normalized_text == "the sky is blue."
    assert len(first.evidence) == 2
    assert first.evidence[0].url == "https://example.com/a"
    # A claim without a verdict derives one from its verifiability score.
    assert second.verdict == "unverifiable"
    assert second.rationale  # a default rationale is generated
    # Persisted copies round-trip through the repository.
    assert repository.get(first.id) == first


def test_save_is_idempotent_per_analysis() -> None:
    """Redelivered completions never duplicate claims."""
    service = ClaimsService(MockClaimRepository())
    analysis = _analysis()

    first = service.save_from_analysis(analysis, _result())
    second = service.save_from_analysis(analysis, _result())

    assert len(first) == 2
    assert second == []


def test_save_skips_analyses_without_claims() -> None:
    """An empty claim list persists nothing."""
    repository = MockClaimRepository()
    service = ClaimsService(repository)
    empty = ClaimAnalysis(claims=[], summary="no claims")

    assert service.save_from_analysis(_analysis(), empty) == []
    assert repository.list_by_analysis(_analysis().analysis_id) == []


def test_verdict_vocabulary_matches_schema() -> None:
    """Every verdict label lives in the schema CHECK vocabulary."""
    result = _result()
    claims = ClaimsService(MockClaimRepository()).save_from_analysis(_analysis(), result)
    assert all(claim.verdict in CLAIM_VERDICTS for claim in claims)


def test_get_returns_claim_or_none() -> None:
    """The service reads back persisted claims and misses cleanly."""
    service = ClaimsService(MockClaimRepository())
    claims = service.save_from_analysis(_analysis(), _result())

    assert service.get(claims[0].id) == claims[0]
    assert service.get(uuid4()) is None
