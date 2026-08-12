"""OpenAI claim analyzer (primary provider, ADR-0006).

The OpenAI client is injected so tests can substitute a fake; production
builds it from settings in the composition root.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

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


class OpenAIClaimAnalyzer(ClaimAnalyzer):
    """ClaimAnalyzer backed by OpenAI chat completions.

    Args:
        client: An ``openai.OpenAI`` client (injected for testability).
        model: The chat model to use.
    """

    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def analyze(self, text: str) -> ClaimAnalysis:
        """Analyze untrusted text through the guarded prompt.

        Raises:
            AnalysisProviderError: When the provider is unreachable.
            GuardedPromptError: When the model returns invalid output.
        """
        content = sanitize_content(text)
        messages = cast(
            list[ChatCompletionMessageParam],
            build_guarded_prompt(SYSTEM_INSTRUCTION, user_content=content, task=CLAIM_TASK),
        )
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:  # normalize provider failures
            raise AnalysisProviderError(f"openai request failed: {exc}") from exc

        raw_content = completion.choices[0].message.content
        if raw_content is None:
            raise GuardedPromptError("model returned empty output")
        try:
            payload = json.loads(raw_content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise GuardedPromptError("model returned non-JSON output") from exc

        validated = validate_structured_output(payload, required_fields=CLAIM_REQUIRED_FIELDS)
        # Stamp the provider + model so persisted verdicts are attributable.
        return replace(parse_claims(validated), model=f"openai:{self._model}")
