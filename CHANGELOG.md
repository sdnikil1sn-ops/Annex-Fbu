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

- **Runtime i18n (Phase 8, ADR-0007).**
  - Versioned translation bundles served from the i18n schema
    (``i18n_locales`` / ``i18n_translations``): ``GET /api/v1/i18n/locales``
    (enabled locales + fallback parents) and
    ``GET /api/v1/i18n/bundles/{locale}`` (resolved bundles).
  - Server-side fallback-chain resolution (requested → parent → … → en)
    in the domain layer (``app.domain.i18n``) — the requested locale wins
    on its own keys, missing keys are filled from the nearest parent.
  - Bundle versioning: responses carry a strong ``ETag`` and
    ``Cache-Control``; passing ``?version=N`` or ``If-None-Match`` yields
    ``304 Not Modified`` for unchanged bundles.
  - ``I18nRepository`` port with PostgreSQL implementation + explicit
    in-memory mock; ``I18nService`` wired into the composition root like
    the other services (503 ``i18n.not_configured`` without a database).
  - Seed migration 20260812000003: locales en/pt/es/fr/de/ar/ja with
    fallback chains and a base translation set (common, analysis, auth,
    errors namespaces; ICU plural category on canonical forms).
  - ``docs/i18n/architecture.md`` — the runtime-i18n contract (bundle
    shapes, fallback algorithm, versioning, plural/RTL handling, adding a
    language, typed-keys lint rule).
  - ``packages/shared_utils`` (Dart): typed ``StringKeys`` registry,
    fallback-chain resolver, ICU plural-category selector, and
    language-tag validation with 23 unit tests; ``.github/workflows/dart.yml``
    runs format/analyze/test for the package in CI.
  - 24 new backend tests (service resolution, bundle API incl. 304/ETag,
    Postgres integration) — 180 backend + 23 Dart tests total.

- **Flutter mobile app — core features (Phase 9).**
  - ``apps/mobile`` (Flutter scaffold, Android/iOS/Windows/Linux/macOS):
    app shell with DI composition root (``AppScope`` + provider), feature-
    first layout (auth, analysis, settings), and runtime i18n wiring.
  - **Analysis flow end-to-end**: ``AnalysisController`` submits text,
    polls ``GET /analysis/{id}`` until terminal, and renders the report
    (credibility ``ScoreMeter``, ``ClaimCard`` per claim) through
    ``shared_ui`` components.
  - **Firebase Auth SDK gateway** (ADR-0005): anonymous, email/password,
    and Google sign-in behind an ``AuthGateway`` port with an explicit
    mock for tests; signed-out users see the sign-in screen.
  - **Runtime i18n client** (ADR-0007): ``I18nController`` loads locales
    and versioned bundles from the backend, resolves typed ``StringKeys``
    with server-resolved fallbacks; language + theme settings screens.
  - **API client**: ``AnalysisApi`` port with ``HttpAnalysisApi`` (bearer
    token, error envelope) and ``MockAnalysisApi`` for local dev/tests.
  - ``packages/shared_models``: analysis, i18n, and user Dart models with
    strict JSON round-trip tests matching the OpenAPI contract (14 tests).
  - ``packages/shared_ui``: design tokens (colors/spacing/typography),
    light/dark themes, and core components — ``AppButton``, ``ScoreMeter``,
    ``ClaimCard``, ``StatusPill`` — with widget tests (9 tests).
  - ``StringKeys`` registry extended with the app's UI keys (analysis,
    auth, settings namespaces); ``.github/workflows/flutter.yml`` runs
    format/analyze/test for the app + Flutter packages in CI.
  - 17 mobile unit/widget tests (controller flows, sign-in gate, full
    submit→report widget flow).

- **Browser extension — full stack (Phase 10).**
  - ``apps/extension``: React + TypeScript Manifest V3 extension (Chrome /
    Edge / Firefox) — typed manifest (``src/manifest.ts``, single source of
    truth emitted as ``dist/manifest.json``) with least-privilege
    permissions and ANNEX-only host permissions.
  - **Background service worker**: context menu ("Verify with ANNEX"), a
    strict typed message router (``handleRequest``) that owns all backend
    traffic — analysis submission/polling, locale/bundle fetches, and auth
    — while content/popup stay network-free; unknown message types fail
    closed.
  - **Content script**: node-based claim-highlighting engine (case-
    insensitive, multi-occurrence) that wraps matches in
    ``<mark class="annex-highlight">`` — never ``innerHTML``, so server
    content is treated as untrusted data (XSS guard); selection bridge for
    the popup and a hard cap on highlighted claims.
  - **Popup app**: pre-fills from the page selection, submits text, polls
    ``GET /analysis/{id}`` until terminal, and renders the credibility
    score + per-claim list with an error/retry affordance.
  - **Options page**: default language, backend API URL, and account
    management persisted in ``chrome.storage.sync``.
  - **Firebase Auth SDK** (ADR-0005): Google popup sign-in behind an
    ``AuthGateway`` port with an explicit mock; ID token flows to the API
    client as the bearer token.
  - **Runtime i18n** (ADR-0007): versioned bundles from the v1 API with a
    typed ``StringKeys`` registry and fallback-chain resolver; the API
    client (``HttpApiClient``) shares the error-envelope contract with the
    Flutter app.
  - **Build**: Vite multi-entry — popup/options React apps plus per-entry
    IIFE bundles for ``background.js``/``content.js`` (MV3 requirement);
    programmatic PNG icon generation (``scripts/generate-icons.mjs``).
  - **Tests**: 33 Vitest tests across shared helpers, the highlighting
    engine (incl. malicious-payload + sanitization guards), the background
    router (incl. context-menu wiring and missing-payload hardening), and
    popup/options component flows (incl. selection-bridge unwrapping)
    — with a jsdom environment and a chrome API mock.
  - **End-to-end harness** (``scripts/e2e.mjs``): loads the built
    ``dist/`` into Chrome for Testing via Puppeteer (dev dependency; the
    installed system Chrome blocks ``--load-extension`` on some machines)
    and drives the full verify-selection flow against a mock v1 backend —
    selection bridge, context-menu marking, claim highlighting, router +
    HTTP client (verify → poll → completed report), and the popup UI. A
    two-launch profile-seeding design exercises the worker's real startup
    composition root (stored API URL) without ``chrome.runtime.reload()``,
    whose worker-target reuse makes CDP re-attachment unreliable. 13
    end-to-end checks.
  - ``.github/workflows/extension.yml`` — typecheck, lint, format, test,
    build, and dist-layout verification in CI.

- **Deployment & release (Phase 11).**
  - `docs/guides/deployment.md` — comprehensive deployment guide:
    target topology, release flow, full configuration reference,
    Supabase migration application, Cloud Run (API + worker services,
    Workload Identity Federation, Secret Manager), managed Redis, the
    Flutter web hosting pipeline (Firebase Hosting), extension store
    packaging, health checks/observability, rollback, troubleshooting,
    and a go-live checklist.
  - `docker/backend.Dockerfile` hardened to a multi-stage build: the
    builder stage installs the pinned package into an isolated prefix;
    the slim non-root runtime copies only runtime artifacts, with OCI
    labels (version stamped by the release pipeline) and the existing
    liveness healthcheck.
  - `docker/compose.prod.yml` — production-ish single-host stack
    (backend + worker + Redis) mirroring the Cloud Run topology, with
    the Firebase service-account JSON injected at runtime via a compose
    secret (never baked into images); every required secret fails fast
    with `:?` interpolation errors.
  - `deploy/cloudrun/` — declarative Cloud Run service manifests:
    `api.yaml` (scales to zero, concurrency 80, Secret Manager refs)
    and `worker.yaml` (one warm instance running the Celery command);
    both omit `FIREBASE_SERVICE_ACCOUNT_PATH` so Firebase Admin uses
    ADC (Workload Identity Federation).
  - `scripts/release.sh` / `scripts/release.ps1` — release cut:
    strict semver validation, clean-tree and duplicate-tag guards,
    CHANGELOG `[Unreleased]` → dated `[X.Y.Z]` section plus a fresh
    `[Unreleased]`, a `chore(repo): release vX.Y.Z` bump commit, and
    the annotated `vX.Y.Z` tag; `--dry-run` preview mode.
  - `.github/workflows/docker.yml` now scans the built image with Trivy
    (CRITICAL/HIGH vulnerabilities fail the build) and uploads the
    SARIF report as an artifact.
  - `.github/workflows/release.yml` — on a `v*` tag push: builds and
    scans the image, publishes it to GHCR (`ghcr.io/<repo>/backend`:
    semver + `latest` tags), then deploys `annex-api` and `annex-worker`
    to Cloud Run via Workload Identity Federation; the deploy job is
    skipped until the Google Cloud secrets are configured.
  - `.github/workflows/security.yml` — dependency vulnerability audits
    on every PR and push to main: `pip-audit` for the backend and
    `npm audit --audit-level=high` for the extension.

- **Flutter Web app & Firebase Hosting (Phase 12).**
  - `packages/shared_features` — the cross-platform Flutter feature layer:
    the API client (+ explicit mock), the runtime i18n controller
    (ADR-0007), the auth gateway with its Firebase implementation and
    mock (ADR-0005), the analysis and settings controllers/screens, and
    the `AppScope` composition root (ADR-0003). The mobile app's feature
    code moved here, so every Flutter app keeps only its platform-specific
    shell, theming, and entry-point code. 14 unit tests.
  - `apps/mobile` refactored onto `shared_features`: the shell
    (`AnnexApp`) and composition root now consume the shared package, and
    the widget suite still covers the full sign-in gate and
    submit → poll → report flow (3 tests).
  - `apps/web` — the real Flutter Web app: a responsive `WebShell`
    (navigation rail on wide viewports, bottom navigation bar on narrow
    ones) reusing every shared feature, a PWA entry (`web/index.html`,
    `web/manifest.json`, generated 192/512 icons via
    `scripts/generate_icons.mjs`), runtime config through `--dart-define`,
    and 4 widget tests covering the sign-in gate, both layouts, and the
    full analysis flow.
  - Firebase Hosting config: `apps/web/firebase.json` (public
    `build/web`, SPA rewrite, immutable caching for hashed assets,
    no-cache service worker) and `.firebaserc` bound to the hosting site.
  - `.github/workflows/flutter.yml` extended to format/analyze/test
    `apps/web` and `packages/shared_features` in CI.
  - `.github/workflows/release.yml` gains a `deploy-web` job: on a `v*`
    tag it builds the web app in release mode (`ANNEX_API_URL`,
    `ANNEX_USE_MOCK=false`) and deploys it to Firebase Hosting via
    `FirebaseExtended/action-hosting-deploy`; skipped until the
    `FIREBASE_SERVICE_ACCOUNT` secret is configured.
  - `docs/guides/deployment.md` §11 updated: the hosting pipeline is now
    implemented end to end (web build → `deploy-web` job → wire
    `ALLOWED_ORIGINS` + Firebase Auth authorized domains).

### Changed

- Root `README.md` and `docs/README.md` updated to the Phase 2 architecture
  baseline (status, links, documentation index).
- Root `README.md`, `docs/README.md`, `docker/README.md`,
  `scripts/README.md`, `.github/workflows/README.md`, and
  `apps/web/README.md` updated for the Phase 11 deployment baseline
  (status, documentation index, script/workflow tables).
- Root `README.md`, `docs/README.md`, `packages/README.md`,
  `apps/mobile/README.md`, `apps/web/README.md`, and
  `.github/workflows/README.md` updated for the Phase 12 web baseline
  (status, package/workflow tables, mobile feature-code relocation).

### Deprecated

- Nothing yet.

### Removed

- Nothing yet.

### Fixed

- **Popup selection pre-fill (Phase 10)**: the popup read
  ``response.text`` from the content script's selection bridge, but the
  bridge answers with the standard envelope (``{ ok, data: { text } }``),
  so the page selection silently never pre-filled. The popup now unwraps
  the envelope; regression tests added.
- **Background router robustness (Phase 10)**: a message with a missing
  payload crashed the handler, which skipped ``sendResponse`` and left the
  caller's ``sendMessage`` promise hanging forever. The router now answers
  malformed messages with ``contracts.missing_payload``.

### Security

- Repository policy established: secrets are never committed
  (see [SECURITY.md](./SECURITY.md)).
- Prompt-injection guard layer (Phase 6) treats user content and model output
  as untrusted data and is verified against adversarial payloads (ADR-0006).
