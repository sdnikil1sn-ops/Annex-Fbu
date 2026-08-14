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
- **Phase 13 (done):** Media pipeline — URL & image analysis.
  ``POST /analysis`` accepts text, URL, and image input. URLs are fetched
  by the SSRF-guarded ``HttpUrlFetcher`` (public-address-only DNS/IP
  guard, capped redirects, size-capped streaming, HTML→text extraction);
  images are decoded at the API boundary with a byte cap and run through
  the Tesseract OCR + OpenCV forensics adapters via the new
  ``MediaPipeline`` application service. Reports carry the media context
  (fetch metadata / OCR + forensics); failures dead-letter to FAILED
  with ``analysis.fetch_failed`` / ``analysis.media_failed``. New
  settings: ``MEDIA_FETCH_TIMEOUT``, ``MEDIA_FETCH_MAX_BYTES``,
  ``MEDIA_IMAGE_MAX_BYTES`` (143 backend tests).
- **Phase 14 (done):** Claims & evidence, Sources & credibility, and the
  Media library. Analyzers now emit per-claim verdicts, evidence links,
  and their model; ``AnalysisService`` persists claims when an analysis
  completes. New services/repositories (PostgreSQL + mocks) and
  endpoints: ``GET /claims/{id}`` (+ ``/evidence``), ``GET /sources``
  (search + profile, public-read), ``POST /media`` (base64 image → OCR +
  forensics) and ``GET /media/{id}``. Sources seed migration
  (``20260812000004_source_seed.sql``). 225 backend tests.
- **Phase 15 (done):** Education lessons — the media-literacy curriculum.
  ``lessons`` / ``lesson_contents`` (per-locale, JSONB sections) /
  ``lesson_progress`` (idempotent per-user completion) with RLS.
  ``EducationService`` expands the user's locale into its fallback chain
  (ADR-0007) and the repository resolves the best content via a lateral
  join ordered over the chain. Endpoints: ``GET /lessons`` (localized
  list + progress), ``GET /lessons/{id}`` (content + sections), and
  ``POST /lessons/{id}/complete`` (first completion wins). Seed migration
  ``20260812000006_lesson_seed.sql``. 242 backend tests.
- **Phase 17 (done):** Educator tools — classes, membership, and lesson
  assignments. ``ClassService`` + ``ClassRepository`` (PostgreSQL +
  mock) coordinate classes owned by their creator (a ``teacher`` member),
  invite-code joining (``ABCDEFGHJKLMNPQRSTUVWXYZ23456789``, 8 chars),
  and assignments unique per (class, lesson). Progress reports derive
  per-student completion by joining members against ``lesson_progress``
  (Phase 15) — no separate progress store. Teacher-only operations are
  guarded at the service boundary and answer ``class.not_found`` (404)
  for non-teachers; the endpoints are optional at the server level
  (``classes.not_configured`` 503 when unwired). Migration
  ``20260813000001_educator.sql``. 270 backend tests.
- **Phase 18 (done):** Community-contributed translations. A
  ``translation_suggestions`` review queue (migration
  ``20260814000001_translation_suggestions.sql``) lets contributors
  propose values for untranslated keys; moderators approve/reject; an
  approved value is published into ``i18n_translations`` with a version
  bump so bundles refresh over the air (ADR-0007). New
  ``TranslationSuggestionRepository`` port + PostgreSQL/mock
  implementations, ``I18nRepository.publish_translation``, and the
  ``TranslationSuggestionService``; endpoints: ``GET
  /i18n/suggestions/missing`` (public), ``POST /i18n/suggestions``
  (token), ``GET /i18n/suggestions`` (own), ``GET
  /i18n/suggestions/pending`` + ``POST /i18n/suggestions/{id}/review``
  (moderator/admin). One open suggestion per (user, locale, key);
  re-submission updates the pending row. 293 backend tests.
- **Phase 19 (done):** Community credibility feedback on the public
  source registry. ``source_feedback`` (migration
  ``20260815000001_source_feedback.sql``) holds one 1–5 rating per
  (source, user), upserted on re-rating; source profiles now carry the
  model credibility score *and* the aggregated community signal
  (``community.count`` / ``community.average``), with ``my_rating``
  surfaced only to authenticated callers. ``SourceRepository.rate`` +
  feedback-aware reads (PostgreSQL + mock), ``SourceService.rate``, and
  ``POST /sources/{domain}/rate``. 305 backend tests.
