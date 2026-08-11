# ADR-0007: Runtime i18n — Unlimited Languages Without Recompiling

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0002

## Context

A core product requirement is **unlimited language support where translations never
require a rebuild**. Flutter's compile-time ARB generation binds strings into the
binary: adding a language means shipping a new app version. The platform instead
needs strings delivered at runtime, with sane fallbacks, plural handling, and RTL
support.

## Decision

- Applications reference **stable, typed string keys** (generated enum/extension from
  a key registry in `shared_utils`); hardcoded user-facing prose is forbidden by
  lint.
- Translations live **server-side**: `i18n_locales` + `i18n_translations` tables
  (see [schema design](../../database/schema-design.md)) served as **versioned locale
  bundles** via `GET /v1/i18n/bundles/{locale}`.
- Clients cache bundles locally; on startup and locale change they fetch the latest
  version; bundles load **asynchronously with a fallback chain**
  `requested locale → parent locale → en` while loading.
- Plural and ICU formatting runs client-side (`intl`); the backend stores canonical
  plural forms per key.
- All layouts are **RTL-ready** from the start (design system requirement).

## Consequences

### Positive

- Adding a language is a server-side data change; app stores are not involved.
- Translations can be corrected over-the-air without a release.

### Negative / Trade-offs

- First launch and locale changes need network (mitigated by offline caching).
- Bundle versioning and cache invalidation must be correct.

### Neutral

- The same bundles feed the browser extension (Phase 10).

## Compliance

- Phase 8 adds a lint rule blocking hardcoded strings in UI code.
- Bundle/fallback logic is unit-tested (missing key → parent → `en`; plural forms).
