# `docker/` — Containerization

Docker assets for ANNEX: local development orchestration and production images.

## Planned contents (implemented in Phase 7 and Phase 11)

```text
docker/
├── compose.dev.yml           # ✅ Local dev: backend, Redis, Celery worker (Phase 7)
├── compose.prod.yml          # ✅ Production-ish services (Cloud Run compatible) — Phase 11
├── backend.Dockerfile        # ✅ API + worker image, multi-stage hardened (Phase 7 → 11)
├── worker.Dockerfile         # (separate image not needed — same runtime, different command)
├── extension.Dockerfile      # (not needed — the extension is a static MV3 build, Phase 10)
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
- **Phase 11 (done):** production compose (`compose.prod.yml`) mirroring the
  Cloud Run topology, multi-stage hardening of `backend.Dockerfile` (builder
  → slim non-root runtime with OCI labels), Trivy image scanning in
  `docker.yml`, Cloud Run service manifests (`deploy/cloudrun/`), and the
  release pipeline (`scripts/release.sh` / `.ps1`,
  `.github/workflows/release.yml`). See `docs/guides/deployment.md`.
