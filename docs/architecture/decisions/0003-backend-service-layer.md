# ADR-0003: Backend Service Layer and Dependency Injection

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0002, ADR-0004

## Context

FastAPI's default style invites business logic into route handlers: a route validates,
authorizes, orchestrates, and queries directly. That produces untestable handlers,
duplicated logic across endpoints, and no single place to enforce authorization. The
backend must follow the project's Service Layer and Repository patterns while keeping
routes thin and the domain isolated.

## Decision

The backend is layered (Clean Architecture, dependency rule pointing inward):

| Layer | Contents | May depend on |
|---|---|---|
| `api` | Routers: validation, auth, serialization. No business logic. | application |
| `application` | Use cases / services: orchestration, authorization checks, transactions | domain, infrastructure (via ports) |
| `domain` | Entities, value objects, domain services, invariants | nothing external |
| `infrastructure` | Repositories, external adapters (Supabase, Redis, OpenAI, Firebase) | domain |

- **Dependency injection** via FastAPI's DI container (and constructor injection in
  services); no service locators or global singletons.
- **Repository pattern**: all data access goes through repositories; callers never
  touch SQL or Supabase clients directly.
- **Authorization is enforced in the service layer**, never only in the UI or the
  router.
- The application is assembled by a factory in `main.py` (lifespan-managed).

## Consequences

### Positive

- Handlers are trivially testable; services are unit-testable with fakes.
- Infrastructure is swappable (e.g., Supabase → another Postgres host) behind ports.
- One enforcement point for security rules.

### Negative / Trade-offs

- More files and indirection than a route-heavy style; teams must learn the layering.

### Neutral

- Slight startup complexity from wiring dependencies at composition root.

## Compliance

- Architecture tests (Phase 3) assert that routers never import repositories and
  application code never imports FastAPI or Supabase SDKs directly.
- Code review checklist in `CONTRIBUTING.md` enforces the layering.
