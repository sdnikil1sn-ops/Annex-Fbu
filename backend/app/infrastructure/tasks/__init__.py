"""Celery worker infrastructure (Phase 7, ADR-0008).

The analysis pipeline runs in a separate worker process:

    celery -A app.infrastructure.tasks.celery_app:celery_app worker

See ``celery_app.py`` (application + delivery semantics), ``analysis_tasks.py``
(the idempotent ``analysis.run`` task with retries and dead-lettering), and
``dispatcher.py`` (the API-side enqueue port implementation).
"""
