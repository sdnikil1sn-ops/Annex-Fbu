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
- **Phase 3:** FastAPI core — config, health, error handling, service layer.
- **Phase 6:** AI, OCR, and image-processing services.
- **Phase 7:** Redis caching and Celery workers.
