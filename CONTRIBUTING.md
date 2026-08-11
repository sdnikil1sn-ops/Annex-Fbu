# Contributing to ANNEX

Thank you for investing your time in ANNEX — the world's most advanced AI-powered
Media & Information Literacy platform. Every contribution, from a typo fix to a new
analysis engine, moves the mission forward.

First, please read our [Code of Conduct](./CODE_OF_CONDUCT.md). By participating you
agree to uphold it.

---

## Table of contents

1. [Development workflow](#development-workflow)
2. [Architecture & coding standards](#architecture--coding-standards)
3. [Code style](#code-style)
4. [Documentation requirements](#documentation-requirements)
5. [Testing requirements](#testing-requirements)
6. [Multilingual (i18n) requirements](#multilingual-i18n-requirements)
7. [Security requirements](#security-requirements)
8. [Pull request process](#pull-request-process)
9. [Review checklist](#review-checklist)

---

## Development workflow

ANNEX is a monorepo managed with [Melos](https://melos.invertase.dev/) for its Dart
workspace and Git for everything else.

1. **Pick or create an issue.** Larger changes should be discussed in an issue first.
   Feature work is organized in phases; see the roadmap in `README.md`.
2. **Fork and branch.** Work on a feature branch named
   `{type}/{short-description}` — e.g. `feat/claim-analysis` or `fix/auth-refresh`.
3. **Commit in small, focused increments** using Conventional Commits
   (see [Commit conventions](#commit-conventions)).
4. **Run the full validation gate** before opening a PR: format, lint, tests.
5. **Open a pull request** against the `main` branch using the PR template.

### Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>
```

- **Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`, `build`, `security`.
- **Scopes:** `mobile`, `web`, `extension`, `backend`, `shared-ui`, `shared-models`,
  `shared-utils`, `db`, `auth`, `ai`, `docs`, `ci`, `repo`.
- **Examples:**
  - `feat(backend): add claim analysis endpoint`
  - `fix(mobile): persist language preference across sessions`
  - `security(auth): enforce rate limits on token refresh`

Never mix unrelated changes in one commit. Never commit secrets, credentials, or
local configuration.

---

## Architecture & coding standards

ANNEX follows strict, company-grade engineering principles. Contributions that
violate them will be sent back for rework.

| Principle | Application |
|---|---|
| **Clean Architecture** | Dependency rule: outer layers (UI, infra) depend inward toward domain; never the reverse. |
| **SOLID** | Single responsibility, open/closed, Liskov, interface segregation, dependency inversion. |
| **DRY** | One source of truth for any logic; reuse `packages/shared_*` instead of copying. |
| **KISS** | Prefer the simplest correct solution. Complexity must earn its place. |
| **Domain-Driven Design** | Ubiquitous language, bounded contexts (e.g. `Claims`, `Sources`, `Media`). |
| **Feature-first layout** | Code is organized by feature, not by technical layer. |
| **Dependency injection** | No service locators, no global singletons for business logic. |
| **Repository pattern** | Data access is abstracted behind repositories; callers never touch Supabase/SQL directly. |
| **Service layer (backend)** | FastAPI routes stay thin; business logic lives in service classes. |
| **MVVM (Flutter)** | UI, state (ViewModel), and model are separated and testable. |
| **OpenAPI-first (backend)** | Every endpoint is documented; clients derive contracts from the spec. |

### Repository boundaries

- `apps/*` — runnable applications. They may depend on `packages/*` but never on each other.
- `packages/*` — reusable libraries with no runtime secrets and no app-specific logic.
- `backend/` — FastAPI service. It is versioned with the monorepo and communicates with
  apps exclusively through its public API.

---

## Code style

- **Dart/Flutter:** `dart format` (2-space indent). Run `dart analyze` with zero issues.
- **Python:** [Ruff](https://docs.astral.sh/ruff/) with the project configuration
  (line length 100, PEP 8 style); `mypy` strict where configured.
- **TypeScript/React:** Prettier + ESLint with the project configuration.
- **Markdown:** one sentence per line where practical; keep headings consistent.
- Line endings are LF everywhere (enforced by `.gitattributes`); do not fight it.

---

## Documentation requirements

- **Every public function/class/endpoint must be documented** in the project's
  documented format (Dart doc comments, Python docstrings, OpenAPI descriptions).
- Non-obvious decisions belong in an Architecture Decision Record (ADR) under
  `docs/architecture/decisions/`.
- User-facing behavior changes update `CHANGELOG.md`.
- No `TODO` comments, no placeholder code, no fake implementations. If something is a
  mock, it must be explicitly named `Mock*` and live behind an interface.

---

## Testing requirements

All contributions must keep the test suites green and extend them where behavior changed:

- **Dart:** unit + widget tests per feature; `flutter test` / `dart test` must pass.
- **Python:** pytest for unit and integration tests; API tests against the FastAPI
  test client; coverage must not regress.
- **TypeScript:** vitest/jest unit tests for extension logic.
- **Security tests** accompany any change to auth, input handling, or prompt boundaries.
- Performance-sensitive changes include benchmarks or at least reasoning in the PR.

---

## Multilingual (i18n) requirements

- Every user-facing string must use a translation key — never hardcoded prose.
- Translations live in locale files and load at runtime; adding a language must
  **never require recompiling** the application.
- New keys must be added to the base locale (English) first, with fallback behavior
  documented.

---

## Security requirements

- Secrets (API keys, service accounts, Firebase config, database passwords) are
  **never** committed. Use environment variables and the project's secret manager.
- All inputs are validated server-side. SQL access goes through the repository layer
  (parameterized / Supabase client) — raw string interpolation into SQL is forbidden.
- LLM prompts must be treated as untrusted: apply the project's prompt-injection
  guards whenever model output or user content is concatenated into prompts.
- Auth decisions follow the documented JWT/OAuth policy; never trust client-supplied
  identity claims.
- When in doubt, open a [security discussion] privately instead of posting details.

---

## Pull request process

1. Update the branch with the latest `main`.
2. Fill out the [pull request template](./.github/PULL_REQUEST_TEMPLATE.md) completely.
3. Request review from at least one maintainer. Respond to feedback in the same PR.
4. The **validation gate** must pass before merge:
   - Formatting check (dart/ruff/prettier)
   - Static analysis (dart analyze / mypy / eslint)
   - All test suites
   - Build of affected apps
5. Squash-merge with a Conventional Commit message.

### Review checklist

- [ ] Architecture principles followed (Clean Architecture, SOLID, DRY, KISS)
- [ ] Feature-first layout respected
- [ ] Public functions documented
- [ ] No TODOs, placeholders, or fake implementations
- [ ] Tests added/updated and passing
- [ ] Lint and format clean
- [ ] User-facing strings use i18n keys
- [ ] No secrets or credentials introduced
- [ ] `CHANGELOG.md` updated where behavior changed

---

*Questions? Open an issue or start a discussion. We're glad you're here.*
