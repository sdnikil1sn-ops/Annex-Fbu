# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Repository foundation (Phase 1).**
  - `LICENSE` — Apache License 2.0.
  - `README.md` — product overview, principles, layout, and stack.
  - `.gitignore` — central secret/exclusion rules for every stack in the monorepo.
  - `.gitattributes` — LF normalization and binary classification.
  - `.editorconfig` — cross-editor formatting defaults.
  - `CONTRIBUTING.md` — contribution workflow, standards, and review process.
  - `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.
  - `SECURITY.md` — vulnerability disclosure and security requirements.
  - GitHub issue templates (bug report, feature request) and pull request template.
  - Monorepo directory scaffold: `apps/`, `backend/`, `packages/`, `docs/`,
    `scripts/`, `docker/`, `.github/` with per-directory README documentation.

- **Architecture blueprint and documentation (Phase 2).**
  - `docs/architecture/overview.md` — C4 system-context and container views.
  - 8 Architecture Decision Records (monorepo/tooling, contracts-first API,
    backend service layer, Supabase PostgreSQL, Firebase Auth, AI provider
    abstraction, runtime i18n, Celery/Redis pipelines) plus an ADR template.
  - 5 Mermaid diagrams: C4 context, C4 containers, analysis component view,
    analysis sequence trace, and the entity-relationship model.
  - `docs/api/v1-endpoints.md` — versioned API endpoint map.
  - `docs/database/schema-design.md` — logical schema, RLS policy matrix.
  - `docs/guides/` — installation, developer guide, and testing strategy.
  - `scripts/validate_repo.py` — repository health checks (YAML, links, required
    files, secret patterns).
  - `.github/workflows/ci.yml` — CI running the validation script on push/PR.

- **Backend core (Phase 3).**
  - FastAPI service layer skeleton (ADR-0003): application factory with DI
    wiring, layered package structure (api/application/domain/infrastructure).
  - `pydantic-settings` configuration (`backend/.env.example` template).
  - Structured logging with request-ID correlation and ASGI request-ID
    middleware (client-supplied IDs never trusted).
  - Unified error envelope (`code`, `message`, `request_id`, `details`) with
    handlers for validation, HTTP, app, and unhandled errors.
  - System endpoints: `GET /health`, `GET /health/ready`, `GET /api/v1/meta/version`,
    CORS middleware.
  - Test suite: 14 tests (config, request-ID, health, error envelope) at ~96%
    coverage; gates `ruff`, `mypy`, `pytest --cov` all green.
  - `scripts/generate_openapi.py` → `docs/api/openapi.yaml` (executable API
    contract, ADR-0002).
  - `.github/workflows/backend.yml` — backend lint/type-check/test CI.

- **Database & repositories (Phase 4).**
  - 6 versioned Supabase migrations (`supabase/migrations/`) implementing the
    full Phase 2 schema (16 tables, indexes, RLS policies on every user table).
  - Domain layer: `Analysis` aggregate with the ADR-0008 state machine
    (validated transitions, structured failure reasons).
  - Repository ports (`app.application.ports`) with a PostgreSQL implementation
    (psycopg, fully parameterized SQL) and an explicitly-named in-memory mock.
  - `AnalysisService` use cases (submit, lifecycle, list with composite-cursor
    pagination, delete).
  - DB-backed readiness probe on `/health/ready` (503 degraded with per-check
    detail); `DATABASE_URL` setting.
  - 33 tests (~98% coverage) including 5 integration tests that apply the
    migrations and exercise the repository against real PostgreSQL; CI now runs
    a Postgres service container for them.

### Changed

- Root `README.md` and `docs/README.md` updated to the Phase 2 architecture
  baseline (status, links, documentation index).

### Deprecated

- Nothing yet.

### Removed

- Nothing yet.

### Fixed

- Nothing yet.

### Security

- Repository policy established: secrets are never committed
  (see [SECURITY.md](./SECURITY.md)).
