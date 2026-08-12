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
from app.application.ports.repositories import AnalysisRepository
from app.application.services.analysis_service import AnalysisService
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.domain.analysis import (
    FAILURE_BLOCKED,
    FAILURE_PROCESSING,
    AnalysisStatus,
)
from app.infrastructure.ai.factory import build_claim_analyzer
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _worker_service(settings: Settings) -> AnalysisService:
    """Build the service the worker executes with.

    Workers are separate processes without ``app.state``, so dependencies
    are constructed here from settings: the PostgreSQL repository (the
    service role bypasses RLS for worker writes) and the configured claim
    analyzer (ADR-0006 provider selection).
    """
    if not settings.database_url:
        raise ConfigurationError(
            "DATABASE_URL is required to run the analysis worker"
        )
    repository: AnalysisRepository = PostgresAnalysisRepository(settings.database_url)
    return AnalysisService(repository)


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
        result = _get_analyzer().analyze(analysis.content or "")
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
    except AnalysisProviderError as exc:
        if self.request.retries < self.max_retries:
            # Transient provider outage: requeue to PENDING, then retry with
            # exponential backoff so the retried run sees a PENDING row.
            service.requeue(processing)
            raise self.retry(exc=exc) from exc
        logger.warning(
            "analysis %s failed permanently after %s attempt(s)",
            analysis_id,
            self.max_retries,
        )
        failed = service.fail(processing, FAILURE_PROCESSING)
        return {
            "analysis_id": analysis_id,
            "status": failed.status.value,
            "failure_reason": failed.failure_reason,
        }

    completed = service.complete_with_report(processing, result)
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
