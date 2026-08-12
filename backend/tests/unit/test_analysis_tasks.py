"""Unit tests for the Celery ``analysis.run`` task (ADR-0008, Phase 7).

The task body is executed eagerly via ``.run()`` with the worker's
dependency builders monkeypatched to mocks, so no broker is required.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.application.ports.ai import AnalysisProviderError, GuardedPromptError
from app.application.services.analysis_service import AnalysisService
from app.domain.analysis import AnalysisInputType, AnalysisStatus
from app.infrastructure.ai.mock_claim_analyzer import MockClaimAnalyzer
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)
from app.infrastructure.tasks import analysis_tasks as tasks
from celery.exceptions import Retry


def _install(monkeypatch: pytest.MonkeyPatch, *, analyzer=None):
    """Point the task at an in-memory service and analyzer."""
    repository = MockAnalysisRepository()
    service = AnalysisService(repository)
    analyzer = analyzer or MockClaimAnalyzer()
    monkeypatch.setattr(tasks, "_worker_service", lambda settings: service)
    monkeypatch.setattr(tasks, "_get_analyzer", lambda: analyzer)
    return repository, analyzer, service


def test_run_analysis_completes_with_report(monkeypatch: pytest.MonkeyPatch) -> None:
    """The happy path completes the analysis from its persisted content."""
    _, analyzer, service = _install(monkeypatch)
    created = service.submit(AnalysisInputType.TEXT, content="some text")

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "completed"
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    assert fetched.status is AnalysisStatus.COMPLETED
    assert fetched.report == {
        "summary": "mock summary",
        "claims": [{"text": "mock claim", "verifiability": 0.5}],
    }
    assert analyzer.analyzed_texts == ["some text"]


def test_run_analysis_skips_already_processed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-delivery of a completed analysis is a no-op (idempotency)."""
    repository, analyzer, service = _install(monkeypatch)
    created = service.submit(AnalysisInputType.TEXT, content="x")
    service.complete(service.mark_processing(created))

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "skipped"
    assert result["reason"] == "terminal:completed"
    assert analyzer.analyzed_texts == []


def test_run_analysis_skips_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deleted-while-queued analysis is skipped, not errored."""
    _, _, _ = _install(monkeypatch)
    result = tasks.run_analysis.run(str(uuid4()))
    assert result["status"] == "skipped"
    assert result["reason"] == "not_found"


def test_run_analysis_blocks_hostile_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """A prompt-guard violation dead-letters without retrying."""

    class GuardedAnalyzer:
        def analyze(self, text: str):
            raise GuardedPromptError("hostile input")

    _, _, service = _install(monkeypatch, analyzer=GuardedAnalyzer())  # type: ignore[arg-type]
    created = service.submit(AnalysisInputType.TEXT, content="evil")

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "failed"
    assert result["failure_reason"] == "analysis.blocked_by_guard"
    assert service.get(created.analysis_id).failure_reason == "analysis.blocked_by_guard"


def test_run_analysis_deadletters_after_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhausted retries dead-letter to FAILED with a provider reason."""

    class FailingAnalyzer:
        def analyze(self, text: str):
            raise AnalysisProviderError("provider down")

    _, _, service = _install(monkeypatch, analyzer=FailingAnalyzer())  # type: ignore[arg-type]
    created = service.submit(AnalysisInputType.TEXT, content="x")
    monkeypatch.setattr(tasks.run_analysis, "max_retries", 0)

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "failed"
    assert result["failure_reason"] == "analysis.processing_failed"
    assert service.get(created.analysis_id).status is AnalysisStatus.FAILED


def test_run_analysis_recovers_stale_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PROCESSING row left by a lost worker is requeued and completed."""
    _, analyzer, service = _install(monkeypatch)
    created = service.submit(AnalysisInputType.TEXT, content="text")
    # Simulate a worker killed mid-task: the row is stuck in PROCESSING.
    service.mark_processing(created)

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "completed"
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    assert fetched.status is AnalysisStatus.COMPLETED
    assert analyzer.analyzed_texts == ["text"]


def test_run_analysis_retries_transient_failure_and_requeues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient provider error requests a retry and requeues to PENDING.

    Celery's ``retry()`` re-raises the original exception inside an except
    block, so the retry request itself is stubbed to raise the Retry signal.
    """

    class FailingAnalyzer:
        def analyze(self, text: str):
            raise AnalysisProviderError("provider down")

    def fake_retry(*args, **kwargs) -> None:
        raise Retry("Task can be retried", None)

    _, _, service = _install(monkeypatch, analyzer=FailingAnalyzer())  # type: ignore[arg-type]
    created = service.submit(AnalysisInputType.TEXT, content="x")
    monkeypatch.setattr(tasks.run_analysis, "retry", fake_retry)

    with pytest.raises(Retry):
        tasks.run_analysis.run(str(created.analysis_id))

    # The attempt was returned to PENDING so the retried run can re-process.
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    assert fetched.status is AnalysisStatus.PENDING
    assert fetched.content == "x"
