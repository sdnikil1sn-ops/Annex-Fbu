"""Shared prompt constants and structured-output parsing.

Provider adapters reuse one system instruction, one task, and one strict
parser so behavior (and its security posture) is identical regardless of
which provider is configured. Since Phase 14 the contract asks the model
for a verdict, rationale, and evidence per claim; missing or invalid
values degrade to a verdict derived from the verifiability score.
"""

from __future__ import annotations

from typing import Any

from app.application.ports.ai import ClaimAnalysis, ClaimItem, EvidenceItem
from app.domain.claim import CLAIM_VERDICTS, derive_verdict
from app.infrastructure.ai.prompt_guard import GuardedPromptError

SYSTEM_INSTRUCTION = (
    "You are ANNEX, a rigorous media-literacy analyst. Extract factual "
    "claims from the provided text and score how verifiable each claim is "
    "(0.0 = not verifiable, 1.0 = fully verifiable), assigning each a "
    "verdict of verifiable, partially_verifiable, unverifiable, true, "
    "false, or misleading with a short rationale."
)

CLAIM_TASK = (
    "Analyze the untrusted text between the markers. Return a JSON object "
    'with exactly two keys: "claims" (a list of objects with "text", '
    '"verifiability", "verdict", "rationale", and "evidence" keys — '
    'evidence is a list of objects with "kind" (link, quote, or source), '
    '"url", "quote", "snippet", and "relevance") and "summary" (a short '
    "neutral summary)."
)

CLAIM_REQUIRED_FIELDS = {"claims", "summary"}


def _parse_evidence(items: Any) -> tuple[EvidenceItem, ...]:
    """Parse the optional evidence list, skipping malformed entries."""
    if not isinstance(items, list):
        return ()
    evidence: list[EvidenceItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        quote = item.get("quote")
        snippet = item.get("snippet")
        evidence.append(
            EvidenceItem(
                kind=str(item.get("kind", "link")),
                url=str(url) if url is not None else None,
                quote=str(quote) if quote is not None else None,
                snippet=str(snippet) if snippet is not None else None,
                relevance=_coerce_relevance(item.get("relevance")),
            )
        )
    return tuple(evidence)


def _coerce_relevance(value: Any) -> float | None:
    """Coerce an evidence relevance to a float, tolerating model drift.

    The prompt asks for a numeric relevance, but models sometimes return a
    short human-readable string instead. Model output is untrusted data, so
    a non-numeric value degrades to ``None`` rather than failing the whole
    analysis (which previously surfaced as ``analysis.processing_failed``).
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_claims(payload: dict[str, Any]) -> ClaimAnalysis:
    """Convert a validated payload into a ClaimAnalysis.

    Args:
        payload: Output already validated by ``validate_structured_output``.

    Returns:
        The typed claim analysis.

    Raises:
        GuardedPromptError: When nested fields are malformed.
    """
    try:
        claims: list[ClaimItem] = []
        for item in payload["claims"]:
            verifiability = float(item["verifiability"])
            verdict = item.get("verdict")
            if not isinstance(verdict, str) or verdict not in CLAIM_VERDICTS:
                verdict = derive_verdict(verifiability)
            claims.append(
                ClaimItem(
                    text=str(item["text"]),
                    verifiability=verifiability,
                    verdict=verdict,
                    rationale=str(item.get("rationale", "")),
                    evidence=_parse_evidence(item.get("evidence")),
                )
            )
        summary = str(payload["summary"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GuardedPromptError("model output fields are malformed") from exc
    return ClaimAnalysis(claims=claims, summary=summary)
