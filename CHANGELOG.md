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

- **Media pipeline — URL & image analysis (Phase 13).**
  - `POST /analysis` now accepts all three input types. **URL** inputs are
    fetched server-side by a new SSRF-guarded fetcher
    (`HttpUrlFetcher`): the scheme must be http(s), the host is resolved
    up front and every address (IPv4/IPv6) must be public, redirects are
    re-validated and capped, and the body is streamed with a timeout and
    a hard size cap. HTML is stripped to visible text (script/style
    excluded, output capped for the analyzer). **Image** inputs are
    decoded at the API boundary (base64 or `data:` URL) with a size cap,
    then OCR (Tesseract) + tamper forensics (OpenCV) extract the text
    and signals to analyze.
  - `MediaPipeline` application service (ADR-0003) turns any input into
    `(text, media_context)`; the report now carries the media context:
    fetch metadata (`input.type`/`url`/`final_url`/`status`) for URLs and
    OCR text/confidence + forensics risk/signals for images.
  - Failure codes `analysis.fetch_failed` (URL) and `analysis.media_failed`
    (image) dead-letter cleanly in the worker; the inline pipeline maps
    them to FAILED analyses — never 5xx. Transient fetch errors retry with
    the existing backoff; undecodable media does not retry.
  - Config: `MEDIA_FETCH_TIMEOUT`, `MEDIA_FETCH_MAX_BYTES`,
    `MEDIA_IMAGE_MAX_BYTES`; wiring in the composition root and the Celery
    worker (`_build_media_pipeline`).
  - `packages/shared_models`: `AnalysisReport` gains an optional
    `MediaContext` (URL fetch metadata or OCR + forensics) with strict
    JSON round-trip tests.
  - Tests: SSRF guard rules (private/reserved ranges, credentials, DNS
    resolution), full fetch path against an in-process HTTP server
    (extraction, redirects, size cap, HTTP errors), pipeline unit tests,
    API submission/failure tests for all three input types, and worker
    media scenarios (143 backend + 18 Dart tests total).

- **Claims & evidence, Sources & credibility, Media library (Phase 14).**
  - Domain aggregates persisted into the already-migrated tables:
    `Claim` + `Evidence` (verifiability verdict vocabulary matching the
    schema CHECK constraint, `derive_verdict` fallback, normalized claim
    text for stable matching), `Source` (credibility score + trust
    signals), and `MediaItem` with `OcrRecord` / `ForensicsRecord`
    children (`claims` / `claim_verdicts` / `evidence`,
    `sources` / `source_scores`, `media_items` / `ocr_results` /
    `forensics_reports`).
  - AI contract extended: analyzers now emit per-claim verdicts, evidence
    links, and their model name; prompt parsing handles the enriched
    response shape, and both the OpenAI and Gemini adapters stamp the
    model. `AnalysisService` persists the claim records (with evidence)
    when an analysis completes.
  - Application services (ADR-0003): `ClaimsService` (owner-scoped
    reads), `SourceService` (public profile + search), `MediaService`
    (image ingest → OCR + forensics persistence). Repository ports +
    PostgreSQL implementations (psycopg, parameterized) and in-memory
    mocks for all three aggregates.
  - New endpoints: `GET /claims/{id}`, `GET /claims/{id}/evidence`,
    `GET /sources/search`, `GET /sources/{domain}`, `POST /media`,
    `GET /media/{id}` — with error codes `claim.not_found`,
    `source.not_found`, `media.not_found`, `media.analysis_not_found`.
  - Sources seed migration (`20260812000004_source_seed.sql`) with
    representative publishers and credibility scores.
  - Tests: unit (claims/media services), API (claims/sources/media),
    integration (repository round-trips against real PostgreSQL), and
    updated analyzer/service/task tests for the enriched contract
    (225 backend + 19 Dart tests total).

- **Education lessons — the media-literacy curriculum (Phase 15).**
  - Schema (``20260812000005_lessons.sql``): ``lessons`` metadata,
    ``lesson_contents`` keyed by (lesson, locale) with a JSONB
    ``sections`` array, and idempotent per-user ``lesson_progress``;
    content and progress read as one aggregate with the caller's
    completion state attached.
  - Localized delivery (ADR-0007): the education service expands the
    user's locale into its fallback chain and the repository resolves
    the best available content via a lateral join ordered by
    ``array_position`` over the chain — a ``pt`` user gets pt content
    where it exists and falls back to en otherwise.
  - Seed migration (``20260812000006_lesson_seed.sql``): four baseline
    lessons (spotting misinformation, credibility scores, image
    verification, claim analysis) with full English content and a
    Portuguese variant for the first lesson to exercise the chain.
  - Endpoints (token-authenticated per the v1 contract):
    ``GET /lessons`` (localized list with progress),
    ``GET /lessons/{id}`` (content + sections), and
    ``POST /lessons/{id}/complete`` (idempotent completion — the first
    timestamp wins). Error codes: ``lesson.not_found``.
  - Tests: service unit tests (chain resolution, idempotency),
    API tests (auth, localization, completion), and repository
    integration tests (242 backend tests total).

- **Lessons in the Flutter apps — web + mobile (Phase 16).**
  - `packages/shared_models`: new `Lesson` / `LessonSection` /
    `LessonProgress` models mirroring the Phase 15 backend contract,
    with strict JSON round-trip tests.
  - `packages/shared_utils`: new typed `StringKeys` for the curriculum
    chrome (tab title, mark-complete, completed, minutes template,
    difficulty names, empty/error) plus a backend i18n seed migration
    (`20260812000007_lesson_i18n.sql`) so the UI strings localize
    through the runtime bundles (ADR-0007).
  - `packages/shared_features`: the `AnalysisApi` interface gains
    `fetchLessons` / `fetchLesson` / `completeLesson` (HTTP + mock); a
    new `LessonsController` drives list/detail/completion with busy and
    error state; a new `LessonsScreen` renders the curriculum list
    (difficulty, minutes, progress) and a lesson detail (content
    sections + idempotent completion).
  - App shells: the web `WebShell` gains a Lessons destination (rail +
    bottom nav) and the mobile `_MainShell` a third tab; both wire a
    `LessonsController` provider and prefetch the curriculum per app
    instance (reloading on locale change).
  - Tests: controller unit tests (localization, completion sync, error
    paths) and web/mobile widget tests covering the full browse → open
    → complete flow (26 shared_models + 21 shared_features + 9 app
    widget tests).

- **Educator tools — classes, membership, and lesson assignments (Phase 17).**
  - New domain aggregate (`app.domain.classroom`): `ClassRoom`,
    `ClassMember`, `Assignment`, `StudentProgress`, `AssignmentProgress`,
    plus the invite-code alphabet and length constants. A class is owned
    by its creator, who becomes a `teacher` member; students join with
    the 8-character invite code (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789` — no
    confusing characters).
  - `ClassRepository` port with a PostgreSQL implementation
    (`class_repository.py`, migration `20260813000001_educator.sql`)
    and an explicit in-memory mock for tests. The owner is inserted into
    `class_members` as `teacher` at creation, so membership is the single
    authorization check; `assignments` are unique per (class, lesson),
    making re-assignment idempotent; RLS policies let members read and
    the owner manage (defense-in-depth, ADR-0004).
  - `ClassService` (application layer) enforces teacher-only operations
    at the service boundary — non-members/non-teachers receive None,
    which the API turns into `class.not_found` so callers can never
    learn whether a class exists.
  - Progress reports join class members against `lesson_progress`
    (Phase 15) — no duplicate progress store. `completed_count` /
    `member_count` ride on each assignment so teachers get at-a-glance
    completion.
  - v1 endpoints (`app/api/v1/classes.py`): `POST /classes`, `GET
    /classes`, `GET /classes/{id}`, `POST /classes/{id}/join`,
    `POST /classes/{id}/assignments` (lesson by UUID or slug),
    `GET /classes/{id}/assignments`, `GET /classes/{id}/progress`,
    `GET /classes/{id}/assignments/{assignment_id}/progress`,
    `DELETE /classes/{id}/assignments/{assignment_id}`,
    `DELETE /classes/{id}/members/{member_id}`, and
    `DELETE /classes/{id}`. Error codes: `class.not_found`,
    `lesson.not_found`, `classes.not_configured` (503 when no class
    service is wired).
  - Tests: service unit tests (invite-code uniqueness, join idempotency,
    teacher-only guards, progress derivation), API tests (create/join/
    assign/progress flows, 404 hiding, 503 unconfigured), and repository
    integration tests (270 backend tests total).

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
- `docs/api/v1-endpoints.md` updated with the Phase 13 media failure codes
  (`analysis.fetch_failed` / `analysis.media_failed`), and the executable
  OpenAPI contract regenerated with the URL/image submit schema (ADR-0002);
  `backend/README.md` documents the Phase 13 media pipeline status.
- `docs/api/v1-endpoints.md` updated with the Phase 14 claims/sources/media
  endpoint contracts and error codes (multipart upload replaced by the
  base64 JSON body, no separate analyze endpoint); `backend/README.md`
  documents the Phase 14 status; OpenAPI contract regenerated.
- `docs/api/v1-endpoints.md` updated with the Phase 15 lessons contract
  (localized list/detail/complete, ``lesson.not_found``); `backend/README.md`
  documents the Phase 15 status; OpenAPI contract regenerated.
- `apps/web/README.md` and `apps/mobile/README.md` updated with the
  Phase 16 lessons feature status.
- `docs/api/v1-endpoints.md` updated with the Phase 17 classes contract
  (create/join/assign/progress routes, invite-code rules, error codes);
  `backend/README.md` documents the Phase 17 status; OpenAPI contract
  regenerated.

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
