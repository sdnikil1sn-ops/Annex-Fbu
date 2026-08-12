"""Explicit mock ClaimAnalyzer for tests and local development."""

from __future__ import annotations

from app.application.ports.ai import ClaimAnalysis, ClaimAnalyzer, ClaimItem


class MockClaimAnalyzer(ClaimAnalyzer):
    """Returns a fixed analysis and records every analyzed text.

    Args:
        result: The analysis to return; defaults to a deterministic sample.
    """

    def __init__(self, result: ClaimAnalysis | None = None) -> None:
        self._result = result or ClaimAnalysis(
            claims=[ClaimItem(text="mock claim", verifiability=0.5)],
            summary="mock summary",
        )
        self.analyzed_texts: list[str] = []

    def analyze(self, text: str) -> ClaimAnalysis:
        """Record the input and return the fixed result."""
        self.analyzed_texts.append(text)
        return self._result
