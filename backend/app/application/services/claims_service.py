"""Claims service — persists analyzer output as domain claims (Phase 14).

Called by the analysis pipeline (inline path and Celery worker) when an
analysis completes; the persisted claims, verdicts, and evidence back the
v1 ``/claims`` endpoints. Saving is idempotent per analysis so redelivered
completions never duplicate rows.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.application.ports.ai import ClaimAnalysis, ClaimItem
from app.application.ports.repositories import ClaimRepository
from app.domain.analysis import Analysis
from app.domain.claim import (
    CLAIM_VERDICTS,
    Claim,
    Evidence,
    derive_verdict,
    normalize_claim_text,
)

logger = logging.getLogger(__name__)


class ClaimsService:
    """Coordinates persistence and retrieval of claims, verdicts, evidence."""

    def __init__(self, repository: ClaimRepository) -> None:
        self._repository = repository

    def save_from_analysis(self, analysis: Analysis, result: ClaimAnalysis) -> list[Claim]:
        """Persist the claims of a completed analysis (idempotent).

        Args:
            analysis: The completed analysis (any state; the aggregate's id
                and owner are what matter).
            result: The analyzer output with per-claim verdicts/evidence.

        Returns:
            The persisted claims, or ``[]`` when the analysis has no claims
            or was already persisted (redelivery guard).
        """
        if not result.claims:
            return []
        if self._repository.list_by_analysis(analysis.analysis_id):
            logger.info("claims already persisted for analysis %s", analysis.analysis_id)
            return []
        claims = [
            self._repository.save(self._to_claim(analysis, index, item, result.model))
            for index, item in enumerate(result.claims)
        ]
        logger.info(
            "persisted %s claims for analysis %s", len(claims), analysis.analysis_id
        )
        return claims

    def get(self, claim_id: UUID) -> Claim | None:
        """Fetch one claim with its verdict and evidence."""
        return self._repository.get(claim_id)

    @staticmethod
    def _to_claim(
        analysis: Analysis, index: int, item: ClaimItem, model: str
    ) -> Claim:
        """Map one analyzer claim item into the persisted aggregate."""
        verdict = (
            item.verdict
            if item.verdict in CLAIM_VERDICTS
            else derive_verdict(item.verifiability)
        )
        rationale = item.rationale or (
            f"Verifiability {item.verifiability:.2f} on the 0-1 scale "
            f"yields a {verdict} verdict."
        )
        return Claim(
            analysis_id=analysis.analysis_id,
            user_id=analysis.user_id,
            claim_index=index,
            text=item.text,
            normalized_text=normalize_claim_text(item.text),
            verdict=verdict,
            confidence=item.verifiability,
            rationale=rationale,
            model=model,
            evidence=tuple(
                Evidence(
                    kind=evidence.kind,
                    url=evidence.url,
                    quote=evidence.quote,
                    snippet=evidence.snippet,
                    relevance=evidence.relevance,
                )
                for evidence in item.evidence
            ),
        )
