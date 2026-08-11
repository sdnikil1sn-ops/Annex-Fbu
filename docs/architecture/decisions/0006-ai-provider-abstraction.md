# ADR-0006: AI Provider Abstraction with Prompt-Injection Guards

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0003, ADR-0008

## Context

ANNEX depends on LLM capabilities (claim decomposition, verifiability scoring,
summarization, embeddings) from OpenAI, with Gemini as an optional second provider.
Providers have incompatible SDKs and models, and — critically — ANNEX feeds
**untrusted user content and model output** into prompts, making prompt injection a
top threat. The AI layer must be swappable, observable, and safe by default.

## Decision

- **Ports (interfaces) per capability**: `ClaimAnalyzer`, `Embedder`, `Summarizer`.
  Each has an **OpenAI adapter (primary)** and a **Gemini adapter (optional)**;
  provider selection is configuration-driven with per-capability model names.
- **Unified guard layer** around every LLM call:
  - User content and prior model output are treated as **untrusted data**, never
    instructions: delimited (not concatenated raw) and labeled as data.
  - Output is validated against a strict schema before use; out-of-schema output is
    rejected and retried or failed cleanly.
  - PII scrubbing before sending; sensitive analysis text is not logged.
- **Observability**: every call records model, tokens, latency, and outcome
  (request-ID correlated) without logging content.
- Long pipelines run in workers (ADR-0008); the API never blocks on model calls.

## Consequences

### Positive

- Provider portability (price/model changes are config, not code).
- Prompt injection and hallucinated-shape failures are caught at the boundary.
- Per-call cost/latency visibility for rate limiting and budgeting.

### Negative / Trade-offs

- Abstraction overhead over raw SDK calls.
- Guard layer must stay current as model behaviors change.

### Neutral

- Embeddings use the same abstraction, enabling future semantic evidence search.

## Compliance

- A prompt-injection **test suite** (Phase 6) verifies the guard layer against
  injection payloads (instruction override, delimiters breakout, role confusion).
- Adapter tests use deterministic fakes; real provider calls are integration-tested
  behind feature flags.
