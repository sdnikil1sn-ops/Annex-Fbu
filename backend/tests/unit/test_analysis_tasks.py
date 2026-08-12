"""Unit tests for the Celery ``analysis.run`` task (ADR-0008, Phase 7).

The task body is executed eagerly via ``.run()`` with the worker's
dependency builders monkeypatched to mocks, so no broker is required.
Phase 13 media scenarios (URL fetch, image OCR/forensics, and their
failure paths) are covered with a media-pipeline-wired service.
"""

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from app.application.ports.ai import AnalysisProviderError, GuardedPromptError
from app.application.ports.media import (
    FetchedPage,
    MediaProcessingError,
    UrlFetchError,
)
from app.application.services.analysis_service import AnalysisService
from app.application.services.media_pipeline import MediaPipeline
from app.domain.analysis import AnalysisInputType, AnalysisStatus
from app.infrastructure.ai.mock_claim_analyzer import MockClaimAnalyzer
from app.infrastructure.media.mock_media_adapters import (
    MockForensicsAdapter,
    MockOcrAdapter,
)
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)
from app.infrastructure.tasks import analysis_tasks as tasks
from celery.exceptions import Retry


def _media_service(
    *,
    fetcher_error: Exception | None = None,
    ocr: MockOcrAdapter | None = None,
) -> AnalysisService:
    """An analysis service wired with the media pipeline of deterministic fakes."""

    class FakeUrlFetcher:
        def fetch(
            self,
            url: str,
            *,
            timeout: float = 10.0,
            max_bytes: int = 2_000_000,
        ) -> FetchedPage:
            if fetcher_error is not None:
                raise fetcher_error
            return FetchedPage(
                final_url="https://example.com/final",
                status=200,
                text="page text",
            )

    return AnalysisService(
        MockAnalysisRepository(),
        media_pipeline=MediaPipeline(
            url_fetcher=FakeUrlFetcher(),
            ocr_adapter=ocr or MockOcrAdapter(),
            forensics_adapter=MockForensicsAdapter(),
        ),
    )


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


# ----------------------------------------------------------------------
# Phase 13 media scenarios
# ----------------------------------------------------------------------


def test_run_analysis_extracts_url_and_reports_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A URL analysis runs the media pipeline and reports its context."""
    service = _media_service()
    analyzer = MockClaimAnalyzer()
    monkeypatch.setattr(tasks, "_worker_service", lambda settings: service)
    monkeypatch.setattr(tasks, "_get_analyzer", lambda: analyzer)
    created = service.submit(
        AnalysisInputType.URL, content="https://example.com/article"
    )

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "completed"
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    media = fetched.report["media"]
    assert media["input"]["type"] == "url"
    assert media["input"]["final_url"] == "https://example.com/final"
    # The analyzer consumed the extracted page text, not the raw URL.
    assert analyzer.analyzed_texts == ["page text"]


def test_run_analysis_extracts_image_and_reports_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An image analysis runs OCR + forensics and reports their output."""
    service = _media_service()
    analyzer = MockClaimAnalyzer()
    monkeypatch.setattr(tasks, "_worker_service", lambda settings: service)
    monkeypatch.setattr(tasks, "_get_analyzer", lambda: analyzer)
    created = service.submit(
        AnalysisInputType.IMAGE,
        content=base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode(),
    )

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "completed"
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    media = fetched.report["media"]
    assert media["input"]["type"] == "image"
    assert media["ocr"]["text"] == "mock ocr text"
    assert media["forensics"]["risk_score"] == 0.0
    assert analyzer.analyzed_texts == ["mock ocr text"]


def test_run_analysis_deadletters_unfetchable_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An SSRF-refused URL dead-letters with the fetch reason, no retry."""
    service = _media_service(fetcher_error=UrlFetchError("refused by the SSRF guard"))
    monkeypatch.setattr(tasks, "_worker_service", lambda settings: service)
    monkeypatch.setattr(tasks, "_get_analyzer", lambda: MockClaimAnalyzer())
    monkeypatch.setattr(tasks.run_analysis, "max_retries", 0)
    created = service.submit(AnalysisInputType.URL, content="http://192.168.1.1/")

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "failed"
    assert result["failure_reason"] == "analysis.fetch_failed"
    fetched = service.get(created.analysis_id)
    assert fetched is not None
    assert fetched.status is AnalysisStatus.FAILED
    assert fetched.failure_reason == "analysis.fetch_failed"


def test_run_analysis_deadletters_media_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An undecodable image dead-letters with the media reason."""

    class BrokenOcr:
        def extract_text(self, image_bytes: bytes):
            raise MediaProcessingError("cannot decode image")

    service = _media_service(ocr=BrokenOcr())  # type: ignore[arg-type]
    monkeypatch.setattr(tasks, "_worker_service", lambda settings: service)
    monkeypatch.setattr(tasks, "_get_analyzer", lambda: MockClaimAnalyzer())
    created = service.submit(
        AnalysisInputType.IMAGE,
        content=base64.b64encode(b"fake-image").decode(),
    )

    result = tasks.run_analysis.run(str(created.analysis_id))

    assert result["status"] == "failed"
    assert result["failure_reason"] == "analysis.media_failed"
    assert service.get(created.analysis_id).failure_reason == "analysis.media_failed"
