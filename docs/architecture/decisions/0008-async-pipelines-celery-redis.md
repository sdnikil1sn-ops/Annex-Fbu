# ADR-0008: Async Analysis Pipelines with Celery and Redis

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0006

## Context

An analysis request can involve OCR, image forensics, and multiple guarded LLM calls
— typically tens of seconds. Blocking the HTTP request would exhaust connections and
give users a poor experience. The pipeline needs asynchronous execution, retries,
visibility, and safe concurrency, plus Redis for rate limiting and hot caches.

## Decision

- **Celery workers** (Redis broker and result backend) execute analysis pipelines;
  the API returns `202 Accepted` with the analysis ID and the client polls
  `GET /v1/analysis/{id}`.
- The analysis **state machine** is explicit: `pending → processing → completed |
  failed` (with structured error). Transitions are persisted in PostgreSQL.
- Tasks are **idempotent** (keyed by `analysis_id`): re-delivery or retry never
  duplicates verdicts.
- Retries use exponential backoff with a max-retry cap; unrecoverable failures go to
  a dead-letter state with a structured reason.
- **Redis** additionally backs: rate-limit counters (auth/analysis/public endpoints)
  and hot caches (locale bundles, source scores).
- Local development runs `backend + worker + Redis` via Docker Compose
  (`docker/compose.dev.yml`, Phase 7).

## Consequences

### Positive

- API stays responsive; workers scale horizontally and independently.
- Long pipelines are observable and resumable (retry/redelivery).

### Negative / Trade-offs

- Eventual consistency: status polling is required; UI must handle pending/failed
  states gracefully.
- Distributed-system complexity: broker availability, task idempotency, and state
  transitions must be tested.

### Neutral

- Rate-limit and cache concerns share the same Redis deployment.

## Compliance

- State-machine tests (Phase 7): every legal/illegal transition is covered.
- Idempotency tests: re-enqueueing the same `analysis_id` produces no duplicates.
- Worker tests run against a real local Redis in CI-adjacent integration jobs.
