"""Shared prompt constants and structured-output parsing.

Provider adapters reuse one system instruction, one task, and one strict
parser so behavior (and its security posture) is identical regardless of
which provider is configured.
"""

from __future__ import annotations

from typing import Any

from app.application.ports.ai import ClaimAnalysis, ClaimItem
from app.infrastructure.ai.prompt_guard import GuardedPromptError

SYSTEM_INSTRUCTION = (
    "You are ANNEX, a rigorous media-literacy analyst. Extract factual "
    "claims from the provided text and score how verifiable each claim is "
    "(0.0 = not verifiable, 1.0 = fully verifiable)."
)

CLAIM_TASK = (
    "Analyze the untrusted text between the markers. Return a JSON object "
    'with exactly two keys: "claims" (a list of objects with "text" and '
    '"verifiability" keys) and "summary" (a short neutral summary).'
)

CLAIM_REQUIRED_FIELDS = {"claims", "summary"}


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
        claims = [
            ClaimItem(
                text=str(item["text"]),
                verifiability=float(item["verifiability"]),
            )
            for item in payload["claims"]
        ]
        summary = str(payload["summary"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GuardedPromptError("model output fields are malformed") from exc
    return ClaimAnalysis(claims=claims, summary=summary)
