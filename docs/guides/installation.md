# ANNEX — Installation Guide

> Phase 2 tooling guide. Running each app is documented in its own phase
> (backend: Phase 3, Flutter: Phase 8, extension: Phase 10). This guide installs and
> verifies the complete toolchain so every later phase compiles on this machine.

## 1. Prerequisites

| Tool | Minimum | Verified in this repo | Needed for |
|---|---|---|---|
| Git | 2.40+ | 2.55.0 | everything |
| Flutter SDK (stable) | 3.35+ | 3.44.8 (Dart 3.12.2) | mobile/web apps + packages |
| Python | 3.12+ | 3.13.14 (Microsoft Store) / 3.14.3 (msys) | backend, validation script |
| Node.js + npm | 20 LTS+ | 25.1.0 / 11.11.0 | browser extension |
| Docker Desktop | 24+ | 29.6.2 | local infra (Redis, Supabase, workers) |
| Supabase CLI | latest | Phase 4 | db/storage migrations |
| Chrome | latest | installed | web + extension development |

## 2. Install the toolchains

### 2.1 Git

Windows: install [Git for Windows](https://git-scm.com/), then verify:

```bash
git --version
git config user.name "Your Name"
git config user.email "you@example.com"
```

### 2.2 Flutter + Dart

Follow the [official Flutter install](https://docs.flutter.dev/get-started/install)
for your OS, then verify:

```bash
flutter --version          # stable channel expected
flutter doctor             # resolve every [!] item before proceeding
```

- **Android:** accept licenses (`flutter doctor --android-licenses`); install Android
  Studio or the command-line SDK.
- **Windows desktop:** install Visual Studio 2022 with the "Desktop development with
  C++" workload.
- **Linux:** `sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev`
  (Debian/Ubuntu).
- **iOS/macOS:** Xcode (latest stable) + CocoaPods; `sudo xcodebuild -license accept`.

### 2.3 Python

```bash
python --version    # 3.12+
```

Create the backend virtual environment (Phase 3 populates it):

```bash
python -m venv backend/.venv
```

### 2.4 Node.js + npm

Install Node 20 LTS or newer (e.g. via [nvm](https://github.com/nvm-sh/nvm) or the
official installer), then verify:

```bash
node --version
npm --version
```

### 2.5 Docker

Install Docker Desktop, start the daemon, verify:

```bash
docker --version
docker info   # must not error
```

### 2.6 Supabase CLI (Phase 4)

```bash
# Windows (scoop) / macOS (brew) / Linux (script) — see Supabase docs
scoop install supabase
supabase --version
```

### 2.7 Validation dependencies

The repository validation script uses PyYAML. Install it into a project virtual
environment (recommended — some Python builds ship without `pip`):

```bash
python -m venv .venv
.venv/bin/python -m pip install pyyaml       # POSIX shells (macOS/Linux/msys)
# or on native Windows: .venv\Scripts\python -m pip install pyyaml
```

## 3. Clone and initialize

```bash
git clone <repository-url> annex
cd annex
git checkout main
.venv/bin/python scripts/validate_repo.py   # must print "Validation PASSED"
```

Melos bootstrap for the Dart workspace happens in Phase 8 (`melos bootstrap`).

## 4. External services (accounts to create)

| Service | What to create | Credentials to keep |
|---|---|---|
| Supabase | Project + buckets (`media`, `avatars`) | Project URL, anon key, service-role key |
| Firebase | Project; enable Google/Apple/email/anonymous providers | Web API key, project ID, per-platform config files |
| OpenAI | API key (analysis models) | `OPENAI_API_KEY` |
| Gemini (optional) | API key | `GEMINI_API_KEY` |
| Redis | Local via Docker (Phase 7) | `REDIS_URL` |

Detailed provider setup with UI walkthroughs is documented in Phase 5 (Firebase)
and Phase 6 (AI providers).

## 5. Environment variables

Never commit real values (`.gitignore`). The backend ships `.env.example` in
Phase 3; the canonical variable set is:

```dotenv
# ANNEX backend — copy to backend/.env and fill in (never commit this file)
APP_ENV=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>

FIREBASE_PROJECT_ID=<project id>
FIREBASE_CLIENT_EMAIL=<service account email>     # for admin ops only
FIREBASE_PRIVATE_KEY=<PEM private key of the Firebase service account>  # secret

OPENAI_API_KEY=<openai key>
GEMINI_API_KEY=<gemini key>      # optional

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

RATE_LIMIT_DEFAULT=120/minute
RATE_LIMIT_ANALYSIS=20/minute
```

## 6. Verify your setup

```bash
git status                      # clean
flutter doctor                  # no outstanding issues
python --version && node --version
docker info                     # daemon running
.venv/bin/python scripts/validate_repo.py  # PASSED
```

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `flutter: command not found` | Add the Flutter `bin` directory to `PATH`; reopen the shell |
| Android licenses prompt | `flutter doctor --android-licenses`, accept all |
| Windows desktop build fails | Install VS 2022 C++ workload; run `flutter doctor -v` |
| `docker info` errors | Start Docker Desktop; on Windows ensure WSL2 backend is enabled |
| `pip install` blocked by policy | Use `--user` (as above) or a venv |
| Git "dubious ownership" on Windows | `git config --global --add safe.directory <repo>` |
| `No such file: pyyaml` during validation | `python -m venv .venv && .venv/bin/python -m pip install pyyaml` |
