# `backend/` — ANNEX API & Workers (FastAPI)

The server-side service layer of ANNEX: a FastAPI application (Python 3.14) plus
Celery workers that power the heavy analysis pipelines.

## Planned contents (implemented from Phase 3 onward)

```text
backend/
├── app/
│   ├── api/                  # Routers (thin), OpenAPI documentation
│   │   └── v1/               # Versioned endpoints
│   ├── core/                 # Config (pydantic-settings), logging, security utils
│   ├── domain/               # Entities, value objects, domain services (DDD)
│   ├── application/          # Use cases / service layer (business logic)
│   ├── infrastructure/       # Repositories, Supabase/Redis/OpenAI adapters
│   ├── jobs/                 # Celery tasks (OCR, enrichment, embeddings)
│   ├── models/               # Pydantic schemas (from OpenAPI contracts)
│   └── main.py               # Application factory, lifespan, DI wiring
├── tests/                    # Unit, integration, API, and security tests
├── alembic/ (or supabase/)   # Database migrations
├── pyproject.toml            # Dependencies and tooling config
└── Dockerfile
```

## Architecture

- **Service-layer architecture**: routes stay thin; business logic lives in the
  `application` layer as injectable services.
- **Repository pattern**: all data access is abstracted; callers never touch
  Supabase/SQL directly.
- **Dependency injection** via FastAPI's DI container (or a lightweight container).
- **OpenAPI-first**: every endpoint documented; clients derive contracts from the
  generated spec.
- **Security**: JWT/Firebase token verification middleware, input validation,
  rate limiting (Redis), prompt-injection guards around all LLM calls.

## Planned services (bounded contexts)

| Context | Responsibility |
|---|---|
| `Claims` | Claim extraction, decomposition, evidence matching |
| `Analysis` | Orchestrates AI, OCR, and image forensics pipelines |
| `Sources` | Publisher/domain credibility scoring |
| `Media` | Image ingestion, OCR (Tesseract), OpenCV forensics |
| `Users` | Profiles, preferences, history |
| `I18n` | Locale management, translation delivery |

## Status

- **Phase 1:** directory documented and reserved.
- **Phase 3 (done):** FastAPI core — config, structured logging, request-ID
  tracing, error envelope, health/meta endpoints, DI wiring.
- **Phase 4 (done):** domain `Analysis` aggregate with state machine, repository
  ports + PostgreSQL implementation (psycopg, parameterized), in-memory mock,
  `AnalysisService` use cases, DB-backed readiness probe. 33 tests (~98%
  coverage), including integration tests against real PostgreSQL (migrations
  applied from `supabase/migrations/`).
- **Phase 5 (done):** Firebase Authentication — token-verifier port (Admin
  SDK + mock), ``get_current_user``/``require_roles`` dependencies, user
  hydration into ``users``/``profiles``, protected ``GET /api/v1/users/me``.
  46 tests (~96% coverage).
- **Phase 6 (done):** AI, OCR, and image-processing services — guarded
  OpenAI/Gemini claim analyzers, Tesseract OCR + OpenCV forensics,
  composition-root factories, and the analysis API (117 tests).
- **Phase 7 (done):** Celery + Redis — async analysis pipeline (ADR-0008)
  with idempotent, retrying, dead-lettering worker tasks; Redis-backed
  rate limiting with a 429 envelope; Redis readiness probe; local dev
  stack (``docker compose -f docker/compose.dev.yml up``) and dev scripts
  (155 tests).
- **Phase 8 (done):** Runtime i18n (ADR-0007) — enabled locales and
  versioned translation bundles served from ``i18n_locales`` /
  ``i18n_translations`` via ``GET /api/v1/i18n/locales`` and
  ``GET /api/v1/i18n/bundles/{locale}`` with server-side fallback-chain
  resolution (requested → parent → en), bundle versioning with
  ``304 Not Modified``/ETag support, and cache headers; seed migration
  covering en/pt/es/fr/de/ar/ja; typed key registry and locale utilities
  in ``packages/shared_utils`` (Phase 8; 179 backend tests + 23 Dart).
