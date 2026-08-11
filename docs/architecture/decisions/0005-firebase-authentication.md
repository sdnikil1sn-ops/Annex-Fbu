# ADR-0005: Firebase Authentication as Identity Provider

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0004

## Context

ANNEX must support sign-in across Android, iOS, Web, Windows, Linux, macOS, and the
browser extension, with Google, Apple, email/password, and anonymous sessions.
Building and operating OAuth flows and token lifecycle for all providers on all
platforms is high-risk, high-effort work with constant security scrutiny. A managed
identity provider that supports every target platform is the pragmatic production
choice.

## Decision

- **Firebase Authentication** is the identity provider. Clients sign in with the
  Firebase SDKs (each platform's official SDK).
- The backend **verifies Firebase ID tokens on every authenticated request**:
  signature, issuer, audience, expiry, and clock-skew checks — never trusts a
  client-supplied identity claim.
- Firebase UID is the primary key of the mirrored `users` table in PostgreSQL
  (ADR-0004), keeping the database decoupled from Firebase internals.
- **RBAC** is stored in the `profiles` table (role column) and mirrored in Firebase
  custom claims for client-side convenience only; the service layer remains the
  authoritative enforcement point (ADR-0003).
- Anonymous sessions may upgrade to full accounts without losing history.

## Consequences

### Positive

- Production-grade OAuth/account security without building it; consistent across all
  seven surfaces.
- Token verification is a single, well-tested middleware path.

### Negative / Trade-offs

- Third-party dependency for a core capability; mitigated by keeping auth behind a
  repository/adapter boundary so a swap is possible.
- Firebase project configuration is per-platform (Google Services, plist, web config)
  and must be injected at build time — never committed as real values.

### Neutral

- Firebase also provides the extension's sign-in flow in Phase 10.

## Compliance

- Middleware tests (Phase 5) include negative cases: expired, malformed,
  wrong-audience, and wrong-issuer tokens.
- No Firebase config or service-account files are committed (`.gitignore` enforced).
