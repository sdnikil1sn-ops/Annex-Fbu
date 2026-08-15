"""Celery implementation of the analysis task dispatcher (ADR-0008)."""

from __future__ import annotations

from uuid import UUID

from celery import Celery

from app.application.ports.tasks import AnalysisTaskDispatcher
from app.core.config import Settings
from app.infrastructure.tasks.celery_app import get_celery_app

# Task name registered on the worker (see analysis_tasks.run_analysis).
ANALYSIS_TASK = "analysis.run"


class CeleryAnalysisTaskDispatcher:
    """Enqueues analyses onto the Celery worker pool.

    The Celery task ID is the analysis ID itself, so result-backend keys
    and the worker's DB-state guard stay consistent (ADR-0008). True
    idempotency comes from the worker: terminal analyses are skipped and
    stale PROCESSING attempts are requeued on at-least-once redelivery.
    """

    def __init__(self, celery_app: Celery) -> None:
        self._app = celery_app

    def dispatch(self, analysis_id: UUID) -> None:
        """Queue the analysis for processing (fire-and-forget)."""
        self._app.send_task(
            ANALYSIS_TASK,
            args=[str(analysis_id)],
            task_id=str(analysis_id),
        )


def build_analysis_task_dispatcher(
    settings: Settings, celery_app: Celery | None = None
) -> AnalysisTaskDispatcher | None:
    """Build the configured dispatcher, or None when no broker is set.

    ``None`` keeps submissions on the interim synchronous path (tests and
    broker-less deployments); a broker enables async processing.

    The dispatcher is built only when an explicit ``CELERY_BROKER_URL`` is
    configured — not when merely ``REDIS_URL`` is set. ``REDIS_URL`` also
    backs the rate limiter and readiness probe, and a deployment that
    configures only Redis (e.g. the Render free tier) has no worker
    process to consume the queue, so submissions would dead-letter
    instead of completing. Requiring the explicit broker keeps such
    deployments on the working inline path while Cloud Run and other
    worker-enabled topologies keep the async pipeline.
    """
    if not settings.celery_broker_url:
        return None
    return CeleryAnalysisTaskDispatcher(celery_app or get_celery_app(settings))
