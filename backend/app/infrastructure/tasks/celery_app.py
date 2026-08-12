"""Celery application factory (ADR-0008).

The analysis worker is a separate process running ``celery -A
app.infrastructure.tasks.celery_app:celery_app worker`` with the same
environment as the API. Task configuration is set here so broker/result
endpoints, serialization, and delivery semantics are defined once.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import Settings, get_settings


def create_celery_app(settings: Settings | None = None) -> Celery:
    """Build a Celery application from the given (or cached) settings.

    The broker and result backend default to ``redis_url`` when the
    dedicated Celery variables are unset, so a single local Redis instance
    covers development. The worker entry point requires a broker: without
    one, starting the worker fails loudly at boot.
    """
    settings = settings or get_settings()
    app = Celery("annex", include=["app.infrastructure.tasks.analysis_tasks"])
    app.conf.update(
        broker_url=settings.celery_broker_url or settings.redis_url,
        result_backend=settings.celery_result_backend or settings.redis_url,
        timezone="UTC",
        enable_utc=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # At-least-once delivery with idempotent tasks (ADR-0008): a lost
        # or crashed worker causes redelivery, never a lost verdict.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        # Analysis pipelines hold provider connections; process one at a
        # time per worker slot.
        worker_max_tasks_per_child=200,
        result_expires=3600,
        task_default_queue="analysis",
        task_routes={
            "analysis.run": {"queue": "analysis"}  # registered task name
        },
    )
    return app


_celery_app: Celery | None = None


def get_celery_app(settings: Settings | None = None) -> Celery:
    """Return the process-wide Celery application, building it once."""
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app(settings)
    return _celery_app


# Worker entry point (``celery -A app.infrastructure.tasks.celery_app worker``).
celery_app = get_celery_app()
