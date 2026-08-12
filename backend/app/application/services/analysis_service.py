"""Analysis service — application-layer use cases for the analysis pipeline."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any
from uuid import UUID

from app.application.ports.ai import (
    AnalysisProviderError,
    ClaimAnalyzer,
    GuardedPromptError,
)
from app.application.ports.repositories import AnalysisRepository, Cursor
from app.domain.analysis import Analysis, AnalysisInputType, AnalysisStatus

logger = logging.getLogger(__name__)


class AnalysisService:
    """Coordinates analysis workflows against an injected repository.

    Args:
        repository: The persistence port (Postgres or in-memory mock).
    """

    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def submit(
        self,
        input_type: AnalysisInputType,
        *,
        user_id: UUID | None = None,
        locale: str = "en",
    ) -> Analysis:
        """Create a pending analysis for later processing.

        Args:
            input_type: The kind of content submitted.
            user_id: Owner; None for anonymous requests.
            locale: Analysis language code.

        Returns:
            The persisted analysis in PENDING state.
        """
        analysis = Analysis(input_type=input_type, user_id=user_id, locale=locale)
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

    def fail(self, analysis: Analysis, reason: str) -> Analysis:
        """Move an analysis into FAILED with a structured reason."""
        updated = analysis.transition_to(AnalysisStatus.FAILED, failure_reason=reason)
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
        """Run the claim-analysis pipeline synchronously (interim, pre-worker).

        Submits the analysis, processes it through the injected analyzer, and
        completes it with the structured report — or fails it with a
        structured reason when the provider errors. ADR-0008 moves this into
        Celery workers; the API keeps the same contract either way.

        Args:
            text: The untrusted content to analyze.
            analyzer: The configured claim analyzer (provider or mock).
            input_type: The kind of content submitted.
            user_id: Owner; None for anonymous requests.
            locale: Analysis language code.

        Returns:
            The completed analysis with its report, or a FAILED analysis
            when the provider cannot produce valid output.
        """
        analysis = self.submit(input_type, user_id=user_id, locale=locale)
        analysis = self.mark_processing(analysis)
        try:
            result = analyzer.analyze(text)
        except (AnalysisProviderError, GuardedPromptError):
            logger.warning(
                "claim analysis failed for analysis %s (provider error)",
                analysis.analysis_id,
            )
            return self.fail(analysis, reason="analysis.processing_failed")
        report = {
            "summary": result.summary,
            "claims": [
                {"text": claim.text, "verifiability": claim.verifiability}
                for claim in result.claims
            ],
        }
        return self.complete(analysis, report=report)

    def delete(self, analysis_id: UUID) -> bool:
        """Delete an analysis; returns True if a row was removed."""
        return self._repository.delete(analysis_id)
