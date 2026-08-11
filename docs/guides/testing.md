# ANNEX — Testing Guide

The testing strategy that keeps ANNEX production-grade across every phase. It
implements the requirements in `CONTRIBUTING.md` (unit, integration, widget, API,
security, accessibility, performance).

## 1. Strategy

Test **the behavior, not the implementation**, following a test pyramid:

1. **Many** fast unit tests (pure logic, models, services with fakes).
2. **Some** integration tests (repositories against a real local Supabase/Redis,
   worker pipelines).
3. **Few** end-to-end tests (API contract tests; UI smoke tests).

Rules:

- Unit tests never touch the network, the filesystem, or the clock.
- Infrastructure is injected (ADR-0003) so tests use fakes/in-memory adapters.
- Every bug fix ships with a regression test first (red → green).

## 2. Test types

| Type | What it covers | Tooling | Where | Threshold |
|---|---|---|---|---|
| Unit | Pure logic, validation, serialization, state machine | `pytest`, `dart test`, `vitest` | per package/service | backend ≥ 85% lines |
| Integration | Repositories ↔ Supabase, adapters ↔ Redis, worker pipelines | `pytest` + real local infra | `backend/tests/integration` | — |
| Widget | Flutter widget behavior + Semantics | `flutter test` | per feature | ≥ 80% (core features) |
| API | Endpoint contracts, authn/authz, error codes | FastAPI `TestClient` | `backend/tests/api` | — |
| Security | Negative authz, rate limits, input fuzzing, prompt injection | `pytest` suites | `backend/tests/security` | — |
| Accessibility | Semantics tree, contrast, focus order | `flutter_test` + axe-core (web) | per UI feature | — |
| Performance | p95 latency budgets, build times, Lighthouse | `pytest-benchmark`, Lighthouse CI | dedicated jobs | documented per phase |

## 3. Running tests

```bash
# Backend (Phase 3+) — from backend/
python -m pip install -e ".[dev]"
ruff check . && mypy app && pytest -q

# Flutter (Phase 8+) — from a package/app directory
dart format --set-exit-if-changed .
dart analyze
flutter test

# Extension (Phase 10+)
npm run lint && npm test

# Everything, everywhere
python scripts/validate_repo.py   # plus stack gates per phase
```

CI mirrors these gates (`.github/workflows/`) on every PR.

## 4. Security test patterns (Phase 5–6)

- **Authz negatives:** for every owner-scoped endpoint, assert 401 (no token),
  403 (other user's resource), and success (owner).
- **Token handling:** expired, malformed, wrong-audience, wrong-issuer tokens are
  rejected (ADR-0005).
- **Rate limits:** hammer an endpoint past its limit and assert `429` + retry-after.
- **Input validation:** fuzz/send unknown fields, oversized payloads, and malformed
  media; assert structured `4xx` with no 5xx leaks.
- **Prompt injection:** the guard layer is probed with instruction-override,
  delimiter-breakout, and role-confusion payloads; model output must never escape
  the response schema (ADR-0006).

## 5. Accessibility tests

- Every interactive widget has a widget test asserting a meaningful Semantics label.
- Web builds run axe-core in CI with WCAG 2.1 AA rules (Phase 8).
- Design-system tokens include contrast-paired values; a token test asserts
  AA contrast ratios for text/background pairs.

## 6. Performance budgets

| Metric | Budget | Verified |
|---|---|---|
| API p95 (non-analysis endpoints) | < 300 ms | Phase 3 |
| Analysis enqueue → completed (no OCR) | < 30 s p95 | Phase 7 |
| Web first-contentful paint | < 1.8 s (mid-tier mobile) | Phase 8 |
| App cold start | < 2.5 s (release build) | Phase 8 |
| Extension popup open | < 500 ms | Phase 10 |

Budgets are checked in dedicated CI jobs, not manually.

## 7. Test data

- Factories/fixtures per service; no production data in tests.
- Database tests run against the Supabase CLI local stack, reset per run.
- Deterministic fakes for AI adapters: golden verdict payloads, no real model calls
  except behind feature-flagged integration jobs.

## 8. Flaky-test policy

A test that fails intermittently is a bug: quarantine it with an issue, fix the
root cause (timing, order dependence, shared state), and never retry-to-green in CI.
