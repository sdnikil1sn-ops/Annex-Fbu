"""AI capability ports (ADR-0006).

The application layer depends on these protocols; infrastructure provides
provider adapters (OpenAI primary, Gemini optional) plus explicit mocks
for tests. Every adapter routes its calls through the prompt guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ClaimItem:
    """One extracted claim with its verifiability score."""

    text: str
    verifiability: float


@dataclass(frozen=True)
class ClaimAnalysis:
    """Structured output of a claim-analysis call."""

    claims: list[ClaimItem]
    summary: str


class AnalysisProviderError(Exception):
    """Raised when an AI provider cannot be reached or returns garbage."""


class GuardedPromptError(Exception):
    """Raised when structured model output fails guard validation.

    Defined at the application boundary so services and the API layer can
    handle provider output failures without depending on infrastructure
    (ADR-0003). ``app.infrastructure.ai.prompt_guard`` re-exports it.
    """


class ClaimAnalyzer(Protocol):
    """Analyzes untrusted text and extracts claims with scores."""

    def analyze(self, text: str) -> ClaimAnalysis: ...


class Summarizer(Protocol):
    """Produces a short, neutral summary of untrusted text."""

    def summarize(self, text: str) -> str: ...


class Embedder(Protocol):
    """Embeds text for similarity search."""

    def embed(self, text: str) -> list[float]: ...
