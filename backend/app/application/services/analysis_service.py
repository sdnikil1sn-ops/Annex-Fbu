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
from app.application.ports.media import MediaProcessingError, UrlFetchError
from app.application.ports.repositories import AnalysisRepository, Cursor
from app.application.ports.tasks import AnalysisTaskDispatcher
from app.application.services.media_pipeline import MediaPipeline
from app.core.exceptions import ConfigurationError
from app.domain.analysis import (
    FAILURE_FETCH,
    FAILURE_MEDIA,
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
        media_pipeline: MediaPipeline | None = None,
    ) -> None:
        self._repository = repository
        self._task_dispatcher = task_dispatcher
        self._media_pipeline = media_pipeline

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
        self,
        analysis: Analysis,
        result: ClaimAnalysis,
        *,
        media: dict[str, Any] | None = None,
    ) -> Analysis:
        """Complete an analysis with the report for an analyzer result.

        Args:
            analysis: The processing analysis to complete.
            result: The claim-analysis output.
            media: Optional media context (Phase 13) merged into the report
                — URL fetch metadata or OCR + forensics signals.
        """
        report = _to_report(result)
        if media is not None:
            report["media"] = media
        return self.complete(analysis, report=report)

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

        Convenience wrapper over :meth:`analyze` for the text path.

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
        return self.analyze(
            input_type,
            content=text,
            analyzer=analyzer,
            user_id=user_id,
            locale=locale,
        )

    def analyze(
        self,
        input_type: AnalysisInputType,
        *,
        content: str,
        analyzer: ClaimAnalyzer,
        user_id: UUID | None = None,
        locale: str = "en",
    ) -> Analysis:
        """Submit any content type for claim analysis and enqueue or run it.

        When the service is bound to a task dispatcher (Phase 7, ADR-0008)
        the submission is enqueued and returned in PENDING state — the
        worker completes it and clients poll. Without a dispatcher the
        pipeline runs inline (tests and broker-less deployments). For URL
        and image inputs the media pipeline (Phase 13) extracts the text
        to analyze (SSRF-guarded fetch / OCR + forensics).

        Args:
            input_type: The kind of content submitted (text, url, image).
            content: The untrusted content: raw text, a URL string, or
                base64-encoded image bytes.
            analyzer: The configured claim analyzer (provider or mock).
            user_id: Owner; None for anonymous requests.
            locale: Analysis language code.

        Returns:
            The PENDING analysis when enqueued, otherwise the completed
            analysis with its report, or a FAILED analysis when the pipeline
            or provider cannot produce valid output.
        """
        analysis = self.submit(
            input_type, user_id=user_id, locale=locale, content=content
        )
        if self._task_dispatcher is not None:
            self._task_dispatcher.dispatch(analysis.analysis_id)
            return analysis
        return self._run_pipeline(analysis, analyzer)

    def extract_content(self, analysis: Analysis) -> tuple[str, dict[str, Any] | None]:
        """Extract the analyzable text (and media context) for an analysis.

        Text inputs pass through untouched; URL and image inputs delegate to
        the bound media pipeline. Shared by the inline path and the Celery
        worker so both behave identically (ADR-0008).

        Args:
            analysis: A non-terminal analysis with persisted content.

        Returns:
            The text for the claim analyzer plus the media context to merge
            into the report (None for text inputs).

        Raises:
            UrlFetchError: The URL could not be fetched safely.
            MediaProcessingError: The image could not be processed.
            ConfigurationError: A media input was submitted without a
                configured media pipeline.
        """
        if analysis.input_type is AnalysisInputType.TEXT:
            return analysis.content or "", None
        if self._media_pipeline is None:
            raise ConfigurationError("media pipeline is not configured")
        return self._media_pipeline.extract(analysis)

    def _run_pipeline(self, analysis: Analysis, analyzer: ClaimAnalyzer) -> Analysis:
        """Run the inline pipeline (interim synchronous path, pre-worker)."""
        processing = self.mark_processing(analysis)
        try:
            text, media = self.extract_content(processing)
            result = analyzer.analyze(text)
        except ConfigurationError:
            # A media input hit a service without a configured pipeline
            # (misconfigured deployment). Never 5xx — fail with the generic
            # processing reason so the contract holds for every submission.
            logger.error(
                "media pipeline missing while processing analysis %s",
                analysis.analysis_id,
            )
            return self.fail(processing, reason=FAILURE_PROCESSING)
        except (AnalysisProviderError, GuardedPromptError):
            logger.warning(
                "claim analysis failed for analysis %s (provider error)",
                analysis.analysis_id,
            )
            return self.fail(processing, reason=FAILURE_PROCESSING)
        except UrlFetchError:
            logger.warning(
                "url fetch failed for analysis %s", analysis.analysis_id
            )
            return self.fail(processing, reason=FAILURE_FETCH)
        except MediaProcessingError:
            logger.warning(
                "media processing failed for analysis %s", analysis.analysis_id
            )
            return self.fail(processing, reason=FAILURE_MEDIA)
        return self.complete_with_report(processing, result, media=media)

    def delete(self, analysis_id: UUID) -> bool:
        """Delete an analysis; returns True if a row was removed."""
        return self._repository.delete(analysis_id)
