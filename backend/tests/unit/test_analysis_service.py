"""Unit tests for the AnalysisService against the mock repository."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.application.ports.ai import (
    AnalysisProviderError,
    ClaimAnalysis,
    ClaimItem,
    GuardedPromptError,
)
from app.application.services.analysis_service import AnalysisService
from app.domain.analysis import (
    AnalysisInputType,
    AnalysisStatus,
    InvalidStatusTransitionError,
)
from app.infrastructure.ai.mock_claim_analyzer import MockClaimAnalyzer
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)


@pytest.fixture()
def service() -> AnalysisService:
    """A service wired to a fresh in-memory repository."""
    return AnalysisService(MockAnalysisRepository())


def test_submit_creates_pending_analysis(service: AnalysisService) -> None:
    """Submitting persists a PENDING analysis for later processing."""
    analysis = service.submit(AnalysisInputType.TEXT, locale="pt-BR")
    assert analysis.status is AnalysisStatus.PENDING
    assert service.get(analysis.analysis_id) is not None
    assert analysis.locale == "pt-BR"


def test_lifecycle_transitions(service: AnalysisService) -> None:
    """pending -> processing -> completed is the happy path."""
    analysis = service.submit(AnalysisInputType.URL)
    processing = service.mark_processing(analysis)
    assert processing.status is AnalysisStatus.PROCESSING

    completed = service.complete(processing)
    assert completed.status is AnalysisStatus.COMPLETED
    assert completed.completed_at is not None
    assert service.get(analysis.analysis_id).status is AnalysisStatus.COMPLETED


def test_fail_requires_reason(service: AnalysisService) -> None:
    """Entering FAILED without a reason is rejected by the domain."""
    analysis = service.submit(AnalysisInputType.IMAGE)
    with pytest.raises(InvalidStatusTransitionError):
        analysis.transition_to(AnalysisStatus.FAILED)


def test_fail_records_reason(service: AnalysisService) -> None:
    """A failed analysis persists its structured failure reason."""
    analysis = service.submit(AnalysisInputType.IMAGE)
    failed = service.fail(analysis, "ocr.unavailable")
    assert failed.status is AnalysisStatus.FAILED
    assert failed.failure_reason == "ocr.unavailable"
    assert failed.completed_at is not None


def test_illegal_transition_is_rejected(service: AnalysisService) -> None:
    """Terminal states are immutable; backwards moves are illegal."""
    analysis = service.submit(AnalysisInputType.TEXT)
    completed = service.complete(service.mark_processing(analysis))
    with pytest.raises(InvalidStatusTransitionError):
        completed.transition_to(AnalysisStatus.PROCESSING)
    with pytest.raises(InvalidStatusTransitionError):
        completed.transition_to(AnalysisStatus.PENDING)


def test_list_and_delete(service: AnalysisService) -> None:
    """Listing is scoped to the owner; deletion removes the row."""
    owner = uuid4()
    other = uuid4()
    first = service.submit(AnalysisInputType.TEXT, user_id=owner)
    second = service.submit(AnalysisInputType.TEXT, user_id=owner)
    service.submit(AnalysisInputType.TEXT, user_id=other)

    ids = [a.analysis_id for a in service.list_for_user(owner)]
    assert ids == [second.analysis_id, first.analysis_id]

    assert service.delete(first.analysis_id) is True
    assert service.get(first.analysis_id) is None
    assert service.delete(first.analysis_id) is False


def test_list_with_cursor(service: AnalysisService) -> None:
    """Cursor pagination returns only rows before the cursor."""
    owner = uuid4()
    first = service.submit(AnalysisInputType.TEXT, user_id=owner)
    second = service.submit(AnalysisInputType.TEXT, user_id=owner)

    page = service.list_for_user(owner, limit=1, cursor=(second.created_at, second.analysis_id))
    assert [a.analysis_id for a in page] == [first.analysis_id]


def test_complete_persists_report(service: AnalysisService) -> None:
    """A report attached at completion is persisted with the row."""
    analysis = service.submit(AnalysisInputType.TEXT)
    report = {"summary": "s", "claims": [{"text": "c", "verifiability": 0.5}]}
    completed = service.complete(service.mark_processing(analysis), report=report)
    assert completed.report == report
    assert service.get(analysis.analysis_id).report == report


def test_analyze_text_completes_with_report(service: AnalysisService) -> None:
    """The synchronous pipeline completes with a structured report."""
    analyzer = MockClaimAnalyzer()
    analysis = service.analyze_text("some text", analyzer=analyzer)
    assert analysis.status is AnalysisStatus.COMPLETED
    # Phase 14: claims carry a verdict, rationale, and evidence.
    assert analysis.report == {
        "summary": "mock summary",
        "claims": [
            {
                "text": "mock claim",
                "verifiability": 0.5,
                "verdict": "partially_verifiable",
                "rationale": "Mock analyzer: verifiability 0.50 is mid-range.",
                "evidence": [
                    {
                        "kind": "link",
                        "url": "https://example.com/evidence",
                        "quote": None,
                        "snippet": None,
                        "relevance": 0.5,
                    }
                ],
            }
        ],
    }
    assert analyzer.analyzed_texts == ["some text"]
    assert service.get(analysis.analysis_id).status is AnalysisStatus.COMPLETED


def test_analyze_text_fails_when_provider_errors(service: AnalysisService) -> None:
    """A provider failure yields a FAILED analysis with a structured reason."""

    class FailingAnalyzer:
        def analyze(self, text: str):
            raise AnalysisProviderError("provider down")

    analysis = service.analyze_text("x", analyzer=FailingAnalyzer())  # type: ignore[arg-type]
    assert analysis.status is AnalysisStatus.FAILED
    assert analysis.failure_reason == "analysis.processing_failed"
    assert analysis.report is None


def test_analyze_text_attaches_owner_and_locale(service: AnalysisService) -> None:
    """Owner and locale flow through the pipeline into the persisted row."""
    owner = uuid4()
    analysis = service.analyze_text(
        "text", analyzer=MockClaimAnalyzer(), user_id=owner, locale="pt-BR"
    )
    assert analysis.user_id == owner
    assert analysis.locale == "pt-BR"


def test_submit_stores_content(service: AnalysisService) -> None:
    """The submitted content is persisted so workers can reprocess by ID."""
    analysis = service.submit(AnalysisInputType.TEXT, content="the untrusted text")
    assert analysis.content == "the untrusted text"
    assert service.get(analysis.analysis_id).content == "the untrusted text"


def test_analyze_text_dispatches_when_worker_configured() -> None:
    """With a dispatcher bound, submission enqueues and stays PENDING."""

    class FakeDispatcher:
        def __init__(self) -> None:
            self.dispatched: list = []

        def dispatch(self, analysis_id) -> None:
            self.dispatched.append(analysis_id)

    dispatcher = FakeDispatcher()
    dispatcher_service = AnalysisService(
        MockAnalysisRepository(), task_dispatcher=dispatcher
    )
    analyzer = MockClaimAnalyzer()

    analysis = dispatcher_service.analyze_text("hello", analyzer=analyzer)

    assert analysis.status is AnalysisStatus.PENDING
    assert dispatcher.dispatched == [analysis.analysis_id]
    # The worker does the actual analysis — nothing ran inline.
    assert analyzer.analyzed_texts == []
    assert dispatcher_service.get(analysis.analysis_id).status is AnalysisStatus.PENDING


def test_requeue_returns_processing_to_pending(service: AnalysisService) -> None:
    """A transiently failed attempt is requeued to PENDING for retry."""
    analysis = service.submit(AnalysisInputType.TEXT, content="x")
    processing = service.mark_processing(analysis)

    requeued = service.requeue(processing)

    assert requeued.status is AnalysisStatus.PENDING
    assert requeued.completed_at is None
    assert requeued.failure_reason is None
    assert requeued.content == "x"
    assert service.get(analysis.analysis_id).status is AnalysisStatus.PENDING


def test_complete_with_report_builds_report_shape(service: AnalysisService) -> None:
    """complete_with_report serializes an analyzer result into the report."""
    analysis = service.submit(AnalysisInputType.TEXT)
    processing = service.mark_processing(analysis)
    result = ClaimAnalysis(
        claims=[ClaimItem(text="c", verifiability=0.9)], summary="s"
    )

    completed = service.complete_with_report(processing, result)

    assert completed.report == {
        "summary": "s",
        "claims": [
            {
                "text": "c",
                "verifiability": 0.9,
                "verdict": "unverifiable",
                "rationale": "",
                "evidence": [],
            }
        ],
    }
    assert service.get(analysis.analysis_id).report == completed.report


def test_analyze_text_guard_error_fails_inline(service: AnalysisService) -> None:
    """The inline fallback fails cleanly on prompt-guard violations."""

    class GuardedAnalyzer:
        def analyze(self, text: str):
            raise GuardedPromptError("hostile")

    analysis = service.analyze_text("evil", analyzer=GuardedAnalyzer())  # type: ignore[arg-type]
    assert analysis.status is AnalysisStatus.FAILED
    assert analysis.report is None
