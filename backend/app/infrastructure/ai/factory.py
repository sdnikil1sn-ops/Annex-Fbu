"""Composition-root factory for the claim analyzer (ADR-0006).

Provider selection is configuration-driven: OpenAI is the primary provider,
Gemini the optional second provider, and the explicit mock backs local
development and tests when no provider key is configured. The SDK clients
are imported lazily so an unconfigured application never loads them.
"""

from __future__ import annotations

from app.application.ports.ai import ClaimAnalyzer
from app.core.config import Settings
from app.infrastructure.ai.mock_claim_analyzer import MockClaimAnalyzer


def build_claim_analyzer(settings: Settings) -> ClaimAnalyzer:
    """Build the configured claim analyzer.

    Args:
        settings: Application settings with provider keys and model names.

    Returns:
        The OpenAI analyzer when ``openai_api_key`` is set, otherwise the
        Gemini analyzer when only ``gemini_api_key`` is set, otherwise the
        explicit mock.
    """
    if settings.openai_api_key:
        from openai import OpenAI

        from app.infrastructure.ai.openai_claim_analyzer import OpenAIClaimAnalyzer

        return OpenAIClaimAnalyzer(
            client=OpenAI(api_key=settings.openai_api_key),
            model=settings.openai_model,
        )
    if settings.gemini_api_key:
        from google import genai

        from app.infrastructure.ai.gemini_claim_analyzer import GeminiClaimAnalyzer

        return GeminiClaimAnalyzer(
            client=genai.Client(api_key=settings.gemini_api_key),
            model=settings.gemini_model,
        )
    return MockClaimAnalyzer()
