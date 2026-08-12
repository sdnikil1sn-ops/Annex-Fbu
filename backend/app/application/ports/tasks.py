"""Async task ports (ADR-0008).

The application layer depends on this protocol to enqueue work; the Celery
implementation lives in ``app.infrastructure.tasks``. Routing tasks through
a port keeps the service layer free of broker coupling (ADR-0003) and lets
tests substitute a fake dispatcher.
"""

from typing import Protocol
from uuid import UUID


class AnalysisTaskDispatcher(Protocol):
    """Enqueues analysis processing onto the asynchronous worker pool."""

    def dispatch(self, analysis_id: UUID) -> None:
        """Queue one analysis for processing; must be idempotent per ID."""
        ...
