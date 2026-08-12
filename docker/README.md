# `docker/` — Containerization

Docker assets for ANNEX: local development orchestration and production images.

## Planned contents (implemented in Phase 7 and Phase 11)

```text
docker/
├── compose.dev.yml           # ✅ Local dev: backend, Redis, Celery worker (Phase 7)
├── compose.prod.yml          # Production-ish services (Cloud Run compatible) — Phase 11
├── backend.Dockerfile        # ✅ API + worker image (Phase 7)
├── worker.Dockerfile         # (separate image not needed — same runtime, different command)
├── extension.Dockerfile      # (optional) static extension build — Phase 10/11
└── .dockerignore
```

## Policy

- **Multi-stage builds** — build artifacts are discarded; runtime images are slim
  and non-root.
- **No secrets in images** — configuration is injected at runtime via environment
  variables or mounted secret files.
- **Healthchecks** — every service image declares a healthcheck the orchestrator
  can rely on.
- Images are built and scanned in CI (`docker.yml`, Phase 11) before any deploy.

## Status

- **Phase 1:** directory reserved.
- **Phase 7 (done):** backend image (shared by the API and the Celery worker),
  the dev compose stack (Redis + backend + worker), and a root `.dockerignore`.
  Start it with `docker compose -f docker/compose.dev.yml up --build` (or
  `scripts/dev.sh` / `scripts/dev.ps1`); the database runs separately via
  `supabase start` (Phase 4).
- **Phase 11:** production compose, multi-stage hardening, image scanning in CI
  (`docker.yml` currently only builds), Cloud Run manifests, and the release
  pipeline.
