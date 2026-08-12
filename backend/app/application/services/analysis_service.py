"""Analysis service — application-layer use cases for the analysis pipeline."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any
from uuid import UUID

from app.application.ports.ai import (
    AnalysisProviderError,
    ClaimAnalysis,
    ClaimAnalyzer,
    GuardedPromptError,
)
from app.application.ports.repositories import AnalysisRepository, Cursor
from app.application.ports.tasks import AnalysisTaskDispatcher
from app.domain.analysis import (
    FAILURE_PROCESSING,
    Analysis,
    AnalysisInputType,
    AnalysisStatus,
)

logger = logging.getLogger(__name__)


def _to_report(result: ClaimAnalysis) -> dict[str, Any]:
    """Serialize a claim analysis into the persisted report shape."""
    return {
        "summary": result.summary,
        "claims": [
            {"text": claim.text, "verifiability": claim.verifiability}
            for claim in result.claims
        ],
    }


class AnalysisService:
    """Coordinates analysis workflows against an injected repository.

    Args:
        repository: The persistence port (Postgres or in-memory mock).
        task_dispatcher: Optional async task port (ADR-0008). When bound,
            submissions are enqueued for the worker pool instead of running
            inline; ``None`` keeps the interim synchronous path (tests and
            deployments without a broker).
    """

    def __init__(
        self,
        repository: AnalysisRepository,
        *,
        task_dispatcher: AnalysisTaskDispatcher | None = None,
    ) -> None:
        self._repository = repository
        self._task_dispatcher = task_dispatcher

    def submit(
        self,
        input_type: AnalysisInputType,
        *,
        user_id: UUID | None = None,
        locale: str = "en",
        content: str | None = None,
    ) -> Analysis:
        """Create a pending analysis for later processing.

        Args:
            input_type: The kind of content submitted.
            user_id: Owner; None for anonymous requests.
            locale: Analysis language code.
            content: The untrusted input, persisted so the worker can
                (re)process the analysis from its ID alone (ADR-0008).

        Returns:
            The persisted analysis in PENDING state.
        """
        analysis = Analysis(
            input_type=input_type, user_id=user_id, locale=locale, content=content
        )
        return self._repository.create(analysis)

    def get(self, analysis_id: UUID) -> Analysis | None:
        """Fetch one analysis by ID."""
        return self._repository.get(analysis_id)

    def list_for_user(
        self, user_id: UUID, *, limit: int = 50, cursor: Cursor | None = None
    ) -> list[Analysis]:
        """List a user's analyses, newest first (cursor-paginated)."""
        return self._repository.list_by_user(user_id, limit=limit, cursor=cursor)

    def mark_processing(self, analysis: Analysis) -> Analysis:
        """Move an analysis into PROCESSING (persists the new state)."""
        updated = analysis.transition_to(AnalysisStatus.PROCESSING)
        return self._repository.update_status(updated)

    def complete(
        self,
        analysis: Analysis,
        *,
        report: dict[str, Any] | None = None,
    ) -> Analysis:
        """Move an analysis into COMPLETED (persists the new state).

        Args:
            analysis: The analysis to complete.
            report: Optional structured report (claims + summary) persisted
                with the completion.
        """
        updated = analysis.transition_to(AnalysisStatus.COMPLETED)
        if report is not None:
            updated = replace(updated, report=report)
        return self._repository.update_status(updated)

    def complete_with_report(
        self, analysis: Analysis, result: ClaimAnalysis
    ) -> Analysis:
        """Complete an analysis with the report for an analyzer result."""
        return self.complete(analysis, report=_to_report(result))

    def fail(self, analysis: Analysis, reason: str) -> Analysis:
        """Move an analysis into FAILED with a structured reason."""
        updated = analysis.transition_to(AnalysisStatus.FAILED, failure_reason=reason)
        return self._repository.update_status(updated)

    def requeue(self, analysis: Analysis) -> Analysis:
        """Return a PROCESSING analysis to PENDING for worker re-delivery.

        Celery retries a transiently failed attempt with exponential backoff
        (ADR-0008); the state machine's ``processing -> pending`` edge lets
        the retried task re-run the pipeline from the persisted content.
        """
        updated = analysis.transition_to(AnalysisStatus.PENDING)
        return self._repository.update_status(updated)

    def analyze_text(
        self,
        text: str,
        *,
        analyzer: ClaimAnalyzer,
        input_type: AnalysisInputType = AnalysisInputType.TEXT,
        user_id: UUID | None = None,
        locale: str = "en",
    ) -> Analysis:
        """Submit text for claim analysis and either enqueue or run it.

        When the service is bound to a task dispatcher (Phase 7, ADR-0008)
        the submission is enqueued and returned in PENDING state — the
        worker completes it and clients poll. Without a dispatcher the
        pipeline runs inline (tests and broker-less deployments).

        Args:
            text: The untrusted content to analyze.
            analyzer: The configured claim analyzer (provider or mock).
            input_type: The kind of content submitted.
            user_id: Owner; None for anonymous requests.
            locale: Analysis language code.

        Returns:
            The PENDING analysis when enqueued, otherwise the completed
            analysis with its report, or a FAILED analysis when the provider
            cannot produce valid output.
        """
        analysis = self.submit(input_type, user_id=user_id, locale=locale, content=text)
        if self._task_dispatcher is not None:
            self._task_dispatcher.dispatch(analysis.analysis_id)
            return analysis
        return self._run_pipeline(analysis, analyzer)

    def _run_pipeline(self, analysis: Analysis, analyzer: ClaimAnalyzer) -> Analysis:
        """Run the inline pipeline (interim synchronous path, pre-worker)."""
        processing = self.mark_processing(analysis)
        try:
            result = analyzer.analyze(analysis.content or "")
        except (AnalysisProviderError, GuardedPromptError):
            logger.warning(
                "claim analysis failed for analysis %s (provider error)",
                analysis.analysis_id,
            )
            return self.fail(processing, reason=FAILURE_PROCESSING)
        return self.complete_with_report(processing, result)

    def delete(self, analysis_id: UUID) -> bool:
        """Delete an analysis; returns True if a row was removed."""
        return self._repository.delete(analysis_id)
