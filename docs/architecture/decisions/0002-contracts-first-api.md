# ADR-0002: Contracts-First API

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0003

## Context

The Flutter clients and the FastAPI backend must agree on every payload that crosses
the wire. Maintaining two hand-written copies of the domain models (Dart classes and
Pydantic schemas) historically drifts: fields are added on one side, renamed on the
other, and serialization mismatches surface only at runtime. The team needs **one
source of truth** for the shape of the data.

## Decision

- Canonical domain contracts live as **JSON Schema** files in
  `packages/shared_models/contracts/`.
- **Dart models are generated from those schemas** (codegen pipeline established in
  Phase 8), so clients and contracts cannot drift.
- The **backend derives its Pydantic models and endpoint documentation from a single
  OpenAPI spec** that references the same contracts.
- API versioning: `/api/v1` prefix. Within a version, changes are **additive only**
  (new optional fields, new endpoints). Breaking changes require a new version.
- Unknown fields are **rejected** at the API boundary (strict validation), never
  silently dropped.

## Consequences

### Positive

- One reviewable artifact per contract change; clients and server move in lockstep.
- OpenAPI documentation is generated, not hand-written.
- Contract changes are diffable and testable (round-trip serialization tests).

### Negative / Trade-offs

- Codegen tooling must be maintained and run in CI (idempotency check).
- Schema reviews add a small step to every API change.

### Neutral

- JSON Schema also serves the browser extension's TypeScript types in Phase 10.

## Compliance

- Generated artifacts are committed; CI verifies regeneration is a no-op
  (`git diff --exit-code` after codegen) from Phase 8 onward.
- Every public model change must include a schema change in the same PR.
