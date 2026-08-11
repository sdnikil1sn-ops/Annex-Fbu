# `docker/` — Containerization

Docker assets for ANNEX: local development orchestration and production images.

## Planned contents (implemented in Phase 7 and Phase 11)

```text
docker/
├── compose.dev.yml           # Local dev: backend, Redis, Celery worker
├── compose.prod.yml          # Production-ish services (Cloud Run compatible)
├── backend.Dockerfile        # FastAPI image
├── worker.Dockerfile         # Celery worker image
├── extension.Dockerfile      # (optional) static extension build
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
- **Phase 7:** backend/worker images and the dev compose stack (with Redis and
  Celery).
- **Phase 11:** production compose, Cloud Run manifests, and the release pipeline.
