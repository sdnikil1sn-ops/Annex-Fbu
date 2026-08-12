# ANNEX — Deployment Guide

> **Phase 11.** How ANNEX ships to production: the release flow, the
> production container stack, and per-target deployment walkthroughs for
> the backend (Cloud Run), database (Supabase), Redis, the Flutter web
> app (Firebase Hosting), and the browser extension.

---

## 1. Target topology

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        M["Mobile App (Flutter)"]
        W["Web App (Firebase Hosting)"]
        E["Browser Extension (Web Store)"]
    end

    subgraph GCP["Google Cloud"]
        CR["Cloud Run — annex-api<br/>(FastAPI, scales to zero)"]
        CW["Cloud Run — annex-worker<br/>(Celery, 1 warm instance)"]
        LG["Cloud Logging"]
    end

    subgraph Data["Data plane"]
        PG[("Supabase PostgreSQL")]
        RD[("Redis (managed)")]
    end

    subgraph External["External services"]
        FA["Firebase Auth"]
        AI["OpenAI / Gemini"]
        OCR["Tesseract OCR"]
        CV["OpenCV"]
    end

    M --> CR
    W --> CR
    E --> CR
    CR --> PG
    CR --> RD
    CR --> FA
    CR --> AI
    CR -->|"enqueue"| CW
    CW --> PG
    CW --> RD
    CW --> OCR
    CW --> CV
    CW --> AI
    CR --> LG
    CW --> LG
```

- **Two Cloud Run services, one image.** `docker/backend.Dockerfile`
  builds a single image for both the API (`annex-api` command) and the
  Celery worker (same image, different command — ADR-0008).
- **Images are immutable, releases are tags.** Every release is a
  `vX.Y.Z` git tag; the release pipeline builds, scans, and publishes
  the image, then (optionally) deploys it.
- **Everything else is managed.** Supabase hosts PostgreSQL; Redis is a
  managed service (Cloud Memorystore / Upstash); Firebase handles
  identity; AI/OCR providers stay external.

---

## 2. Environments and promotion

| Environment | Purpose | Database | Traffic |
|---|---|---|---|
| `staging` | Pre-release validation with real providers | Supabase project (staging) | dev/QA only |
| `production` | Public traffic | Supabase project (production) | all clients |

Promote by **re-tagging and redeploying the same image** — an artifact
already scanned and tested in staging is promoted to production; it is
never rebuilt. The env var `APP_ENV` distinguishes the two (controls
`DEBUG`/docs UI and reload behavior).

---

## 3. Prerequisites

| Tool | Used for |
|---|---|
| [Supabase CLI](https://supabase.com/docs/guides/cli) | Link project, apply migrations, manage secrets (`supabase secrets`) |
| [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) | `gcloud run` deploys, Secret Manager |
| [Firebase CLI](https://firebase.google.com/docs/cli) | Web app hosting, extension store tooling |
| [Docker](https://docs.docker.com/get-docker/) | Local production dress rehearsal (`compose.prod.yml`) |

Accounts: Supabase project(s), Google Cloud project, Firebase project
(shared with auth, Phase 5), OpenAI (and optionally Gemini) keys,
managed Redis.

---

## 4. Configuration reference

All backend settings are environment variables (Twelve-Factor;
`backend/app/core/config.py`). Secrets go to **Secret Manager / compose
secrets**, never into images, manifests, or the repository.

| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | ✅ | `staging` or `production` |
| `LOG_LEVEL` | | `INFO` in production |
| `ALLOWED_ORIGINS` | ✅ | JSON array, e.g. `["https://app.annex.example"]` |
| `DATABASE_URL` | ✅ | Supabase **pooled** URL (`postgresql://…:6543/…`) |
| `REDIS_URL` | ✅ | Managed Redis endpoint |
| `CELERY_BROKER_URL` | | Defaults to `REDIS_URL` when unset |
| `CELERY_RESULT_BACKEND` | | Defaults to `REDIS_URL` when unset |
| `FIREBASE_PROJECT_ID` | ✅ | Used for the Admin SDK + audience check |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | opt. | Path to service-account JSON; omit on Cloud Run (ADC) |
| `OPENAI_API_KEY` | ✅ | Primary claim analyzer (ADR-0006) |
| `OPENAI_MODEL` | | `gpt-4o-mini` |
| `GEMINI_API_KEY` | opt. | Second analyzer provider |
| `GEMINI_MODEL` | | `gemini-2.5-flash` |
| `OCR_LANGUAGES` | | `eng` (Tesseract codes) |
| `RATE_LIMIT_DEFAULT` | | `120/minute` |
| `RATE_LIMIT_ANALYSIS` | | `20/minute` |
| `I18N_DEFAULT_LOCALE` | | `en` (fallback-chain root) |
| `I18N_BUNDLE_CACHE_TTL` | | `300` (seconds) |

---

## 5. Release flow

```mermaid
flowchart LR
    A["scripts/release.sh 0.2.0"] --> B["changelog bump + tag v0.2.0 (local)"]
    B --> C["git push origin main + tag"]
    C --> D["GitHub Actions: release.yml"]
    D --> E["build + Trivy scan (fail on CRITICAL/HIGH)"]
    E --> F["publish ghcr.io/<repo>/backend:0.2.0"]
    F --> G["deploy annex-api + annex-worker to Cloud Run"]
```

1. **Cut the release** (from a clean tree on `main`):

   ```bash
   scripts/release.sh 0.2.0            # or scripts\release.ps1 0.2.0 on Windows
   ```

   The script validates the semver, moves the `CHANGELOG.md`
   `[Unreleased]` section into a dated `[0.2.0]` section, prepends a
   fresh `[Unreleased]`, commits the bump, and creates the annotated tag
   `v0.2.0`. Use `--dry-run` to preview.

2. **Push** — the tag push triggers `release.yml`:

   ```bash
   git push origin main
   git push origin v0.2.0
   ```

3. **Pipeline** — `.github/workflows/release.yml`:
   - builds the image from the **tagged tree** (reproducible release),
   - scans it with Trivy (any CRITICAL/HIGH vulnerability fails),
   - publishes to `ghcr.io/<repo>/backend` (`0.2.0`, `0.2`, `latest`),
   - deploys both Cloud Run services when the Google Cloud secrets are
     configured (see [§7.4](#74-connect-the-pipeline)).

4. **Verify** — hit the liveness and readiness probes after deploy
   (see [§9](#9-health-checks-and-observability)).

> Version policy: `X.Y.Z` semver; pre-release tags (`v0.2.0-rc.1`) build
> and publish but the deploy job is typically triggered manually from
> stable tags only.

---

## 6. Database (Supabase)

1. **Link the project:**

   ```bash
   supabase link --project-ref <project-ref>
   ```

2. **Apply migrations** (all schema + RLS policies, Phase 4):

   ```bash
   supabase db push
   ```

   Migrations are additive and versioned under `supabase/migrations/`;
   destructive changes ship as explicit `drop` migrations with review.

3. **Verify RLS** — every table carries row-level security (migration
   `20260811000006_rls.sql`); the API uses the **service-role** key for
   server-side access while clients never touch the database directly.

4. **Keep `DATABASE_URL` as a secret** in Secret Manager (pooled
   connection string, port 6543) — never in a manifest or repo.

---

## 7. Backend on Cloud Run

### 7.1 Create the secrets

Create one Secret Manager secret per secret setting, then grant the
Cloud Run service account access:

```bash
gcloud secrets create annex-database-url --replication-policy=automatic
printf '%s' "postgresql://postgres:...@aws-0-<region>.pooler.supabase.com:6543/postgres" \
  | gcloud secrets versions add annex-database-url --data-file=-

# repeat for: annex-redis-url, annex-celery-broker-url,
# annex-celery-result-backend, annex-openai-api-key, annex-gemini-api-key

gcloud secrets add-iam-policy-binding annex-database-url \
  --member="serviceAccount:<service-account-email>" --role="roles/secretmanager.secretAccessor"
```

### 7.2 Identity: Workload Identity Federation

The API verifies Firebase tokens with the Admin SDK. On Cloud Run,
**omit `FIREBASE_SERVICE_ACCOUNT_PATH`** and let the Admin SDK use
Application Default Credentials (the Cloud Run service account) — no
credential file to mount or rotate. Firebase itself validates the
tokens; the backend only needs `FIREBASE_PROJECT_ID`.

If you prefer a dedicated service account, mount its JSON as a Secret
volume and point `FIREBASE_SERVICE_ACCOUNT_PATH` at it.

### 7.3 Deploy the services

The declarative manifests live in `deploy/cloudrun/`. After
substituting the `<placeholders>` (project id, image ref, secret
names, service-account email, app domain):

```bash
gcloud run services replace deploy/cloudrun/api.yaml --region <region>
gcloud run services replace deploy/cloudrun/worker.yaml --region <region>
```

Or deploy from the command line:

```bash
gcloud run deploy annex-api \
  --image ghcr.io/<owner>/backend:0.2.0 \
  --region <region> \
  --service-account <service-account-email> \
  --min-instances 0 --max-instances 10 \
  --concurrency 80 --memory 512Mi --cpu 1 \
  --set-env-vars APP_ENV=production,LOG_LEVEL=INFO,\
FIREBASE_PROJECT_ID=<firebase-project-id> \
  --set-secrets DATABASE_URL=annex-database-url:latest,\
REDIS_URL=annex-redis-url:latest,...
```

**The worker** runs the same image with the Celery command
(`deploy/cloudrun/worker.yaml`). It is a long-running process, so it
deploys with `minScale: 1` and no HTTP concurrency. Cloud Run may
recycle idle instances; Celery redelivers broker tasks after the
visibility timeout, so a recycle is safe. For very heavy pipelines,
run the same image on a long-lived host (Compute Engine, GKE, or a
plain VM with `docker compose -f docker/compose.prod.yml up -d`).

### 7.4 Connect the pipeline

Configure repository secrets (or an environment for staging):

| Secret / variable | Value |
|---|---|
| `GOOGLE_CLOUD_PROJECT` | GCP project id |
| `GOOGLE_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GOOGLE_SERVICE_ACCOUNT` | service account email |
| `GOOGLE_CLOUD_REGION` (variable) | e.g. `us-central1` |

Create the WIF provider + service account via
[google-github-actions/auth](https://github.com/google-github-actions/auth)
docs. Until these are set, the `deploy-cloudrun` job is skipped and
`release.yml` still publishes the image.

---

## 8. Redis

Celery broker, result backend, and rate-limit counters share one Redis
endpoint in production (the URLs fall back to `REDIS_URL` when unset).
Use a managed instance (Cloud Memorystore, Upstash, or similar) with:

- **TLS** (`rediss://…`) — the backend's `redis` client connects
  natively.
- **Password authentication** stored in `annex-redis-url`.
- A **logical separation** (database index or separate instance) for
  broker vs. rate-limit traffic if the throughput warrants it.

---

## 9. Health checks and observability

| Probe | Endpoint | Purpose |
|---|---|---|
| Liveness | `GET /health` | Container healthcheck + Cloud Run start check |
| Readiness | `GET /health/ready` | 503 with per-dependency detail when DB/Redis degrade |

The Docker image declares a `HEALTHCHECK` against `/health`. On Cloud
Run, `startup-cpu-boost` is enabled in the manifests to speed cold
starts.

- **Logs** stream to Cloud Logging; every request carries
  `X-Request-ID` (client-supplied IDs are never trusted) — correlate
  logs by it.
- **AI calls** log model, tokens, and latency only — never content.
- **Metrics to watch**: p95 API latency (< 300 ms budget), enqueue →
  completed analysis time (< 30 s p95, Phase 7), rate-limit 429 counts,
  worker queue depth (Celery + Redis `llen`).

---

## 10. Rollback

Every deploy is a **revision**; Cloud Run keeps the last 999 revisions
and traffic can be pinned to any of them:

```bash
gcloud run services update-traffic annex-api --to-revisions=annex-api-<revision>=100
gcloud run services update-traffic annex-worker --to-revisions=annex-worker-<revision>=100
```

Roll back the image instead when the fix belongs in code: re-tag the
previous commit, push, and let `release.yml` redeploy.

**Database rollbacks** are restore-based (Supabase point-in-time
recovery) — never roll forward on a partially applied additive
migration.

---

## 11. Web app (Firebase Hosting)

> The Flutter Web entry (`apps/web`) is scaffolded; the hosting pipeline
> activates when the web build exists. This section is the Phase 11
> contract for it.

1. `flutter build web` (from the monorepo web app) produces `build/web`.
2. `firebase init hosting` in `apps/web` — public dir `build/web`,
   single-page app rewrite, and a `.firebaserc` bound to the hosting
   site.
3. Deploy with `firebase deploy --only hosting` (manual) or a
   `firebase-hosting-merge` GitHub Action job triggered after the
   Flutter CI build (Phase 11 `release.yml` extension).
4. Point `ALLOWED_ORIGINS` at the hosting URL (`https://<site>.web.app`)
   and whitelist it in Firebase Auth authorized domains.

---

## 12. Browser extension release

The extension is a static MV3 build (`apps/extension/dist` after
`npm run build` — typed manifest, IIFE bundles, icons).

1. `cd apps/extension && npm ci && npm run build`
2. **Chrome Web Store** — zip `dist/`, upload via the developer
   dashboard (private listing for staging, public for production),
   bump `version` in `src/manifest.ts` per release.
3. **Firefox Add-ons** — MV3 files require a signed distribution
   (`web-ext lint`/`sign`); the build output is shared.

Extensions authenticate with the user's Firebase session; no secrets
ship in the bundle (least-privilege permissions, Phase 10).

---

## 13. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health/ready` → 503 | DB/Redis unreachable from the service | Check `DATABASE_URL`/`REDIS_URL` secrets + VPC/egress; see `/health/ready` detail |
| API 503 `i18n.not_configured` | DB not reachable at startup | Verify migrations applied (`supabase db push`) |
| 429s in production | Rate limits too tight for real traffic | Adjust `RATE_LIMIT_*` env vars |
| Worker not consuming | Broker URL mismatch API vs worker | Both services must use the same `CELERY_BROKER_URL` |
| Firebase auth 401 | Wrong audience/project | Confirm `FIREBASE_PROJECT_ID` matches the client Firebase project |
| Trivy fails release | A CRITICAL/HIGH vulnerability | Fix the dependency, cut a new release (never suppress) |
| Cold start latency | Scaled-to-zero instance | `run.googleapis.com/startup-cpu-boost` (already in manifests) or `minScale: 1` |

---

## 14. Checklist before go-live

- [ ] Migrations applied to production Supabase; RLS verified
- [ ] All secrets in Secret Manager; none in the repo/images
- [ ] `scripts/validate_repo.py` passes
- [ ] Release pipeline green on a staging tag; image scanned
- [ ] `/health` and `/health/ready` healthy in production
- [ ] `ALLOWED_ORIGINS` + Firebase authorized domains updated
- [ ] Rollback revision pinned and tested
