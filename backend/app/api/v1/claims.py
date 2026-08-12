"""Claims endpoints — v1 contract (Phase 14).

Claims are persisted when their analysis completes; these endpoints expose
the structured verdict + evidence record for owner-scoped retrieval.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_claims_service_dep, get_current_user
from app.api.errors import AppError
from app.application.services.claims_service import ClaimsService
from app.domain.claim import Claim, Evidence
from app.domain.user import User

router = APIRouter(prefix="/claims", tags=["claims"])


def _evidence_payload(evidence: Evidence) -> dict[str, Any]:
    return {
        "id": str(evidence.id),
        "kind": evidence.kind,
        "url": evidence.url,
        "quote": evidence.quote,
        "snippet": evidence.snippet,
        "relevance": evidence.relevance,
    }


def _claim_payload(claim: Claim) -> dict[str, Any]:
    return {
        "id": str(claim.id),
        "analysis_id": str(claim.analysis_id),
        "claim_index": claim.claim_index,
        "text": claim.text,
        "normalized_text": claim.normalized_text,
        "verdict": claim.verdict,
        "confidence": claim.confidence,
        "rationale": claim.rationale,
        "model": claim.model,
    }


@router.get("/{claim_id}")
def get_claim(
    claim_id: UUID,
    user: User = Depends(get_current_user),
    service: ClaimsService = Depends(get_claims_service_dep),
) -> dict[str, Any]:
    """Fetch one claim with its verdict and rationale (owner only)."""
    claim = service.get(claim_id)
    if claim is None or claim.user_id != user.id:
        # Do not reveal whether the claim exists.
        raise AppError("claim.not_found", "Claim not found.", status_code=404)
    return {"data": _claim_payload(claim)}


@router.get("/{claim_id}/evidence")
def get_claim_evidence(
    claim_id: UUID,
    user: User = Depends(get_current_user),
    service: ClaimsService = Depends(get_claims_service_dep),
) -> dict[str, Any]:
    """Fetch the evidence links supporting a claim's verdict (owner only)."""
    claim = service.get(claim_id)
    if claim is None or claim.user_id != user.id:
        raise AppError("claim.not_found", "Claim not found.", status_code=404)
    return {"data": [_evidence_payload(item) for item in claim.evidence]}
