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

- **Authentication & security (Phase 5).**
  - Firebase ID-token verification behind a ``TokenVerifier`` port: Admin SDK
    implementation + explicit mock for tests (ADR-0005).
  - ``get_current_user`` dependency (Bearer parsing, 401 envelope, hydration)
    and ``require_roles`` RBAC factory (403 envelope).
  - ``User`` domain entity + ``UserRepository`` port with PostgreSQL and
    in-memory implementations; ``UserService.get_or_create`` mirrors Firebase
    identities into ``users``/``profiles`` on first login.
  - Protected endpoint ``GET /api/v1/users/me``.
  - 46 tests (~96% coverage) including 8 Postgres integration tests.

- **AI & media processing (Phase 6).**
  - AI capability ports (``ClaimAnalyzer``, ``Summarizer``, ``Embedder``) with
    OpenAI (primary) and Gemini (optional) adapters routing every call through
    one guarded prompt, plus an explicit mock for tests and local development
    (ADR-0006).
  - Prompt-injection guard layer: untrusted content is delimited and labeled as
    data (never instructions), control characters are stripped with a length
    cap, and structured model output is validated against an exact schema
    contract that rejects missing, extra, and malformed fields.
  - Media-processing ports (``OcrAdapter``, ``ForensicsAdapter``) with a
    Tesseract OCR adapter and an OpenCV error-level-analysis forensics adapter,
    plus explicit mocks; shared ``ConfigurationError`` for missing
    prerequisites (e.g. the Tesseract binary).
  - Provider settings (``OPENAI_API_KEY``/``OPENAI_MODEL``,
    ``GEMINI_API_KEY``/``GEMINI_MODEL``, ``OCR_LANGUAGES``) and pinned
    dependencies (``openai``, ``google-genai``, ``pytesseract``,
    ``opencv-python-headless``).
  - Composition-root factories wiring the configured provider into
    ``app.state``: ``build_claim_analyzer`` (OpenAI → Gemini → explicit mock),
    ``build_ocr_adapter`` (Tesseract with a logged mock fallback when the
    binary is missing), and ``build_forensics_adapter`` (OpenCV);
    ``create_app`` accepts override-injectable analyzers/adapters like the
    auth ports (tests inject mocks).
  - Analysis API (v1 contract): ``POST /analysis`` (202 + ``analysis_id``;
    text input only at this phase), ``GET /analysis/{id}`` and
    ``GET /analysis`` (owner-scoped, cursor-paginated), and
    ``DELETE /analysis/{id}``. The pipeline runs inline through the bound
    analyzer and persists the report — the interim synchronous path until
    ADR-0008 workers land in Phase 7; anonymous submissions supported.
  - ``report jsonb`` column on ``analyses`` (migration 20260812000001) so
    reports are fetchable by ID; ``GuardedPromptError`` promoted to the
    application boundary so services handle provider output failures without
    infrastructure coupling.
  - 71 new tests covering adversarial prompt-injection payloads, analyzer
    adapters against deterministic fakes, media adapters against real images,
    composition-root wiring, the analysis API, and the jsonb report
    adaptation (117 tests total, ~94% coverage); the executable OpenAPI
    contract is regenerated with the new paths (ADR-0002).

- **Async pipelines & rate limiting (Phase 7).**
  - Celery worker (``app.infrastructure.tasks``) executing the analysis
    pipeline asynchronously (ADR-0008): idempotent ``analysis.run`` task
    keyed by ``analysis_id`` (broker-level task-ID dedup + PENDING-state
    guard), exponential-backoff retries with a requeue-to-PENDING retry edge
    in the state machine, and dead-lettering to FAILED with structured
    reasons (``analysis.processing_failed`` / ``analysis.blocked_by_guard``).
  - ``content`` column on ``analyses`` (migration 20260812000002) so the
    worker reprocesses from the persisted input by ID alone.
  - ``AnalysisTaskDispatcher`` port + Celery implementation: the analysis
    service enqueues when a broker is configured and keeps the interim
    synchronous path otherwise (same ``202 + analysis_id`` contract; clients
    poll ``GET /analysis/{id}``).
  - Redis-backed fixed-window rate limiting (``RATE_LIMIT_DEFAULT`` /
    ``RATE_LIMIT_ANALYSIS``) enforced by an ASGI middleware per client +
    endpoint scope with the standard 429 envelope; a no-op fallback (with a
    logged warning) keeps dev/tests broker-free; Redis readiness probe on
    ``/health/ready``.
  - Local dev stack: ``docker/compose.dev.yml`` (Redis + API + worker),
    ``docker/backend.Dockerfile`` (non-root, healthcheck),
    ``scripts/dev.sh``/``dev.ps1``, and ``.github/workflows/docker.yml``
    image-build CI.
  - 38 new tests: full state-machine matrix, worker task (happy path,
    idempotency, guard block, retry requeue, dead-letter), rate-limit
    parsing/windows/429s, dispatcher wiring, and Redis integration
    (155 tests total, ~94% coverage).

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
- Prompt-injection guard layer (Phase 6) treats user content and model output
  as untrusted data and is verified against adversarial payloads (ADR-0006).
