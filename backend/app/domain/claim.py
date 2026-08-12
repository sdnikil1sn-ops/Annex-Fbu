"""Claim aggregate — extracted claims with verdicts and evidence (Phase 14).

Persisted into ``claims`` / ``claim_verdicts`` / ``evidence`` when an
analysis completes. The verdict vocabulary mirrors the schema CHECK
constraint; ``derive_verdict`` is the fallback when an analyzer emits no
verdict (mapping the numeric verifiability score to the closest label).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

# The verdict vocabulary persisted in ``claim_verdicts`` (schema CHECK).
CLAIM_VERDICTS = frozenset(
    {
        "verifiable",
        "partially_verifiable",
        "unverifiable",
        "true",
        "false",
        "misleading",
    }
)

# Verifiability thresholds mapping a numeric score to a fallback verdict.
_VERIFIABLE_THRESHOLD = 0.7
_PARTIAL_THRESHOLD = 0.4


def derive_verdict(verifiability: float) -> str:
    """Map a ``0..1`` verifiability score to a fallback verdict label.

    High scores are ``verifiable``, mid scores ``partially_verifiable``,
    and low scores ``unverifiable``. Used when the analyzer did not emit a
    verdict for a claim.
    """
    if verifiability >= _VERIFIABLE_THRESHOLD:
        return "verifiable"
    if verifiability >= _PARTIAL_THRESHOLD:
        return "partially_verifiable"
    return "unverifiable"


def normalize_claim_text(text: str) -> str:
    """Normalize a claim for stable matching (lowercase, collapsed spaces)."""
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class Evidence:
    """One piece of evidence supporting a claim verdict."""

    id: UUID = field(default_factory=uuid4)
    kind: str = "link"  # link | quote | source
    url: str | None = None
    quote: str | None = None
    snippet: str | None = None
    relevance: float | None = None


@dataclass(frozen=True)
class Claim:
    """A persisted claim with its verdict, rationale, and evidence."""

    analysis_id: UUID
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    claim_index: int = 0
    text: str = ""
    normalized_text: str = ""
    verdict: str = "unverifiable"
    confidence: float = 0.0
    rationale: str = ""
    model: str = ""
    evidence: tuple[Evidence, ...] = ()
