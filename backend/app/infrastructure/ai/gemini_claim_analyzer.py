"""Gemini claim analyzer (optional provider, ADR-0006).

Implements the same ``ClaimAnalyzer`` port as the OpenAI adapter so the
provider is a configuration choice, not a code fork.
"""

from __future__ import annotations

import json

from google import genai
from google.genai import types as genai_types

from app.application.ports.ai import (
    AnalysisProviderError,
    ClaimAnalysis,
    ClaimAnalyzer,
)
from app.infrastructure.ai.prompt_guard import (
    GuardedPromptError,
    build_guarded_prompt,
    sanitize_content,
    validate_structured_output,
)
from app.infrastructure.ai.prompts import (
    CLAIM_REQUIRED_FIELDS,
    CLAIM_TASK,
    SYSTEM_INSTRUCTION,
    parse_claims,
)


class GeminiClaimAnalyzer(ClaimAnalyzer):
    """ClaimAnalyzer backed by the Gemini API.

    Args:
        client: A ``google.genai.Client`` (injected for testability).
        model: The model name, e.g. ``gemini-2.5-flash``.
    """

    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    def analyze(self, text: str) -> ClaimAnalysis:
        """Analyze untrusted text through the guarded prompt.

        Raises:
            AnalysisProviderError: When the provider is unreachable.
            GuardedPromptError: When the model returns invalid output.
        """
        content = sanitize_content(text)
        system, user = build_guarded_prompt(
            SYSTEM_INSTRUCTION, user_content=content, task=CLAIM_TASK
        )
        try:
            response = self._client.models.generate_content(
                model=self._model,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system["content"],
                    response_mime_type="application/json",
                    temperature=0,
                ),
                contents=user["content"],
            )
        except Exception as exc:  # normalize provider failures
            raise AnalysisProviderError(f"gemini request failed: {exc}") from exc

        if response.text is None:
            raise GuardedPromptError("model returned empty output")
        try:
            payload = json.loads(response.text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise GuardedPromptError("model returned non-JSON output") from exc

        validated = validate_structured_output(payload, required_fields=CLAIM_REQUIRED_FIELDS)
        return parse_claims(validated)
