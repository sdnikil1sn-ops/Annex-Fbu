"""In-memory ClaimRepository for unit tests (explicit mock)."""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import ClaimRepository
from app.domain.claim import Claim


class MockClaimRepository(ClaimRepository):
    """A deterministic in-memory store implementing the claim port."""

    def __init__(self) -> None:
        self._store: dict[UUID, Claim] = {}

    def save(self, claim: Claim) -> Claim:
        """Store and return the claim."""
        self._store[claim.id] = claim
        return claim

    def get(self, claim_id: UUID) -> Claim | None:
        """Return the stored claim or None."""
        return self._store.get(claim_id)

    def list_by_analysis(self, analysis_id: UUID) -> list[Claim]:
        """Return the claims of one analysis, in claim order."""
        claims = [c for c in self._store.values() if c.analysis_id == analysis_id]
        claims.sort(key=lambda c: c.claim_index)
        return claims
