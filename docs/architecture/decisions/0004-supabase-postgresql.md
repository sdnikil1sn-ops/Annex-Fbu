# ADR-0004: Supabase PostgreSQL as Primary Store

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers
- **Related:** ADR-0003

## Context

ANNEX needs a relational store with robust security, media storage, and minimal
operational burden. Options considered: self-managed PostgreSQL (full control, full
ops cost), a NoSQL store (poor fit for relational claims/evidence/scores), and a
managed Postgres platform. Supabase provides managed PostgreSQL, object storage,
and an auth-adjacent ecosystem with **Row-Level Security (RLS)** — a defense-in-depth
mechanism that enforces row visibility at the database level.

## Decision

- **Supabase PostgreSQL** is the primary database; **Supabase Storage** holds media
  objects.
- All data access from the backend goes through repositories (ADR-0003) using
  parameterized queries — **raw SQL string interpolation is forbidden**.
- Transport (Phase 4): repositories connect directly to the Supabase PostgreSQL
  endpoint via `DATABASE_URL` using `psycopg` (row-parameterized); local
  development targets the Supabase CLI local stack. RLS remains the database-level
  boundary for interactive clients; the service role / superuser bypasses RLS for
  worker writes.
- **RLS is enabled on every user-data table** as defense-in-depth: even if an
  application bug leaks a query, rows the user cannot see are not returned.
- Schema and migrations are managed in the repository with the **Supabase CLI**;
  migrations are versioned, reviewable files.
- Buckets use the **least-privilege policy**; objects are served via **signed URLs
  with short expiry**.

## Consequences

### Positive

- Managed backups, scaling, and monitoring; RLS adds a database-level security
  boundary independent of application code.
- Storage and database share one platform and one auth model.

### Negative / Trade-offs

- Vendor coupling; mitigated by the repository pattern and portable SQL migrations.

### Neutral

- Local development uses a Supabase CLI stack (Docker) for parity with production.

## Compliance

- Migrations committed and reviewable; `supabase db reset` reproduces the schema.
- RLS policies are covered by tests in Phase 4 (unauthenticated/unauthorized rows
  are invisible).
