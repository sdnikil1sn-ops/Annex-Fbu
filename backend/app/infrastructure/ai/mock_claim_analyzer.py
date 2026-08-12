"""Explicit mock ClaimAnalyzer for tests and local development."""

from __future__ import annotations

from app.application.ports.ai import ClaimAnalysis, ClaimAnalyzer, ClaimItem, EvidenceItem


class MockClaimAnalyzer(ClaimAnalyzer):
    """Returns a fixed analysis and records every analyzed text.

    Args:
        result: The analysis to return; defaults to a deterministic sample
            carrying a verdict, rationale, and evidence (Phase 14 shape).
    """

    def __init__(self, result: ClaimAnalysis | None = None) -> None:
        self._result = result or ClaimAnalysis(
            claims=[
                ClaimItem(
                    text="mock claim",
                    verifiability=0.5,
                    verdict="partially_verifiable",
                    rationale="Mock analyzer: verifiability 0.50 is mid-range.",
                    evidence=(
                        EvidenceItem(
                            kind="link",
                            url="https://example.com/evidence",
                            relevance=0.5,
                        ),
                    ),
                )
            ],
            summary="mock summary",
            model="mock",
        )
        self.analyzed_texts: list[str] = []

    def analyze(self, text: str) -> ClaimAnalysis:
        """Record the input and return the fixed result."""
        self.analyzed_texts.append(text)
        return self._result
