"""Analysis worker task (ADR-0008).

``run_analysis`` executes the claim-analysis pipeline for one analysis in
the worker process. It is **idempotent by construction**: terminal
analyses (COMPLETED/FAILED) are skipped on re-delivery, the task ID equals
the analysis ID (consistent result-backend keys + DB guard), and a stale
PROCESSING row — a worker lost mid-task, redelivered at-least-once — is
requeued and reprocessed instead of being skipped forever.

Transient provider failures are retried with exponential backoff; the
attempt is requeued to PENDING before retrying so the state machine stays
consistent (``processing -> pending`` edge). Unrecoverable failures —
retries exhausted or hostile content blocked by the prompt guard —
dead-letter to FAILED with a structured reason.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from celery.app.task import Task

from app.application.ports.ai import (
    AnalysisProviderError,
    ClaimAnalyzer,
    GuardedPromptError,
)
from app.application.ports.media import MediaProcessingError, UrlFetchError
from app.application.ports.repositories import AnalysisRepository
from app.application.services.analysis_service import AnalysisService
from app.application.services.media_pipeline import MediaPipeline
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.domain.analysis import (
    FAILURE_BLOCKED,
    FAILURE_FETCH,
    FAILURE_MEDIA,
    FAILURE_PROCESSING,
    AnalysisStatus,
)
from app.infrastructure.ai.factory import build_claim_analyzer
from app.infrastructure.media.factory import build_media_pipeline
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _worker_service(settings: Settings) -> AnalysisService:
    """Build the service the worker executes with.

    Workers are separate processes without ``app.state``, so dependencies
    are constructed here from settings: the PostgreSQL repository (the
    service role bypasses RLS for worker writes), the configured claim
    analyzer (ADR-0006 provider selection), and the media pipeline
    (Phase 13, cached per process like the analyzer).
    """
    if not settings.database_url:
        raise ConfigurationError(
            "DATABASE_URL is required to run the analysis worker"
        )
    repository: AnalysisRepository = PostgresAnalysisRepository(settings.database_url)
    return AnalysisService(repository, media_pipeline=_get_media_pipeline())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="analysis.run",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_analysis(self: Task, analysis_id: str) -> dict[str, Any]:
    """Process one analysis; retries transient failures, never duplicates.

    Args:
        analysis_id: The analysis UUID as a string (the Celery task ID).

    Returns:
        A small status dict describing the outcome for observability.
    """
    service = _worker_service(get_settings())
    parsed = UUID(analysis_id)

    analysis = service.get(parsed)
    if analysis is None:
        # Deleted while queued — nothing to do.
        return {"analysis_id": analysis_id, "status": "skipped", "reason": "not_found"}
    if analysis.status in {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}:
        # Idempotency guard: re-delivery of an already-terminal analysis
        # is a no-op (ADR-0008).
        return {
            "analysis_id": analysis_id,
            "status": "skipped",
            "reason": f"terminal:{analysis.status.value}",
        }
    if analysis.status is AnalysisStatus.PROCESSING:
        # At-least-once redelivery after a lost worker: the attempt that
        # marked PROCESSING never finished, so requeue it (legal
        # PROCESSING -> PENDING retry edge) and reprocess from the
        # persisted content — stale attempts must not wedge the analysis.
        analysis = service.requeue(analysis)

    processing = service.mark_processing(analysis)
    try:
        text, media = service.extract_content(processing)
        result = _get_analyzer().analyze(text)
    except GuardedPromptError:
        # Hostile input is unrecoverable — retrying cannot help. Dead-letter
        # immediately with a distinct reason.
        logger.warning("analysis %s blocked by the prompt guard", analysis_id)
        failed = service.fail(processing, FAILURE_BLOCKED)
        return {
            "analysis_id": analysis_id,
            "status": failed.status.value,
            "failure_reason": failed.failure_reason,
        }
    except MediaProcessingError:
        # An image that cannot be decoded/processed will never succeed on
        # retry — dead-letter with the media reason.
        logger.warning("analysis %s failed media processing", analysis_id)
        failed = service.fail(processing, FAILURE_MEDIA)
        return {
            "analysis_id": analysis_id,
            "status": failed.status.value,
            "failure_reason": failed.failure_reason,
        }
    except (AnalysisProviderError, UrlFetchError) as exc:
        # Fetch errors are retried alongside provider outages because a
        # network blip is indistinguishable from a refusal at this layer;
        # permanent refusals (SSRF guard, size cap) simply exhaust the
        # retries and dead-letter below — wasteful but harmless.
        if self.request.retries < self.max_retries:
            # Transient provider/fetch outage: requeue to PENDING, then
            # retry with exponential backoff so the retried run sees a
            # PENDING row.
            service.requeue(processing)
            raise self.retry(exc=exc) from exc
        logger.warning(
            "analysis %s failed permanently after %s attempt(s)",
            analysis_id,
            self.max_retries,
        )
        reason = FAILURE_FETCH if isinstance(exc, UrlFetchError) else FAILURE_PROCESSING
        failed = service.fail(processing, reason)
        return {
            "analysis_id": analysis_id,
            "status": failed.status.value,
            "failure_reason": failed.failure_reason,
        }

    completed = service.complete_with_report(processing, result, media=media)
    logger.info("analysis %s completed with %s claims", analysis_id, len(result.claims))
    return {"analysis_id": analysis_id, "status": completed.status.value}


_analyzer_instance: ClaimAnalyzer | None = None


def _get_analyzer() -> ClaimAnalyzer:
    """Build (and cache) the claim analyzer from settings.

    The indirection keeps provider SDK imports out of the worker's import
    path until the first task actually needs them.
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = build_claim_analyzer(get_settings())
    return _analyzer_instance


_media_pipeline_instance: MediaPipeline | None = None


def _get_media_pipeline() -> MediaPipeline:
    """Build (and cache) the media pipeline from settings.

    Cached like the analyzer so the adapter construction — and the
    Tesseract fallback probe with its warning — runs once per worker
    process instead of once per task.
    """
    global _media_pipeline_instance
    if _media_pipeline_instance is None:
        _media_pipeline_instance = build_media_pipeline(get_settings())
    return _media_pipeline_instance
