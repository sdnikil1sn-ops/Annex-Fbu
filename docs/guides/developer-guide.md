# ANNEX — Developer Guide

How to work effectively inside the ANNEX monorepo. Standards are in
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) (authoritative); this guide is the
day-to-day playbook.

## 1. Repository tour

| Path | What lives there |
|---|---|
| `apps/mobile/` | Flutter app (Android/iOS/Win/Linux/macOS) — Phase 8+ |
| `apps/web/` | Flutter Web entry + PWA — Phase 8+ |
| `apps/extension/` | React + TS browser extension — Phase 10 |
| `backend/` | FastAPI service layer + Celery workers — Phase 3+ |
| `packages/shared_models/` | Canonical contracts (JSON Schema + Dart) |
| `packages/shared_ui/` | Flutter design system |
| `packages/shared_utils/` | Pure-Dart utilities |
| `docs/` | Architecture, ADRs, diagrams, API, DB, guides |
| `scripts/` | Cross-platform automation (incl. `validate_repo.py`) |
| `docker/` | Compose files and images |
| `.github/` | Issue/PR templates, CI/CD workflows |

## 2. Day-to-day loop

```bash
git checkout -b feat/my-change
# ... implement ...
python scripts/validate_repo.py   # always: must PASS
git add . && git commit -m "feat(scope): concise description"
git push -u origin feat/my-change
# open a PR against main using the template
```

### Commit message cheat sheet

`type(scope): description` — types: `feat fix refactor docs test chore ci perf
build security`; scopes: `mobile web extension backend shared-ui shared-models
shared-utils db auth ai docs ci repo`.

## 3. How a feature ships (end-to-end example)

**Feature: "sentiment signal on claims"** — the standard path:

1. **Contract** (`packages/shared_models/contracts/`) — add `sentiment` to the claim
   schema; regenerate Dart models (Phase 8 codegen).
2. **Backend service** (`backend/app/application/`) — extend the claim analyzer
   port + implementation; add the guarded prompt (ADR-0006).
3. **Endpoint** (`backend/app/api/v1/`) — extend the claim response (additive,
   ADR-0002); update docs if the shape changes.
4. **Client feature** (`apps/mobile/lib/features/...`) — render the signal; add i18n
   keys (ADR-0007).
5. **Tests** — schema round-trip, service unit test, endpoint integration test,
   widget test.
6. **Docs** — update `CHANGELOG.md`; API doc if needed.
7. **PR** — fill the template; validation gate must pass.

## 4. Adding a language (no rebuild)

1. Insert a row in `i18n_locales` (e.g. `pt-BR`, fallback `pt`).
2. Insert translations in `i18n_translations` for the locale.
3. Publish via the API (`GET /api/v1/i18n/bundles/pt-BR`).
4. Clients pick it up on next bundle refresh — **no app release required**.

## 5. Adding an ADR

1. Copy [`docs/architecture/decisions/template.md`](../architecture/decisions/template.md)
   to the next number: `NNNN-short-title.md`.
2. Fill Context / Decision / Consequences / Compliance.
3. Reference the ADR from the affected code or docs so the decision is discoverable.

## 6. Updating diagrams

Diagrams are Mermaid in `docs/architecture/diagrams/` — render on GitHub and in
VS Code (Mermaid preview extension). Keep the canonical file and the render in
`overview.md` in sync when the level-1/level-2 views change.

## 7. Validation gate

| Check | Command | Phase |
|---|---|---|
| Repository health | `python scripts/validate_repo.py` | 2+ |
| Backend lint/test | `ruff check . && mypy app && pytest` | 3+ |
| Flutter analyze/test | `dart format --set-exit-if-changed && dart analyze && flutter test` | 8+ |
| Extension lint/test | `npm run lint && npm test` | 10+ |

CI runs the same gates (`.github/workflows/`); what passes locally must pass there.

## 8. Debugging

- **Request IDs:** every API response carries `X-Request-ID`; grep logs by it.
- **Local stack:** `docker compose -f docker/compose.dev.yml up` (Phase 7) for
  Redis/worker parity.
- **DB:** `supabase db reset` recreates the schema from migrations (Phase 4).
- **AI calls:** the AI guard layer logs model, tokens, and latency per request —
  never content.

## 9. Common mistakes

- Committing `.env` or platform Firebase configs (`.gitignore` blocks these).
- Skipping the schema when changing a payload (ADR-0002).
- Putting business logic in a router (ADR-0003).
- Hardcoding user-facing strings (ADR-0007).
