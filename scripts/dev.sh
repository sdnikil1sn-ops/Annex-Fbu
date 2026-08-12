#!/usr/bin/env bash
# =====================================================================
# ANNEX — local dev stack (Phase 7)
# Starts Redis, the FastAPI service, and the Celery analysis worker via
# the docker compose dev stack. Idempotent: safe to re-run.
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# DATABASE_URL is required by the backend container (compose fails loudly
# when unset). Local Supabase default is used when not provided.
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@host.docker.internal:54322/postgres}"

docker compose -f docker/compose.dev.yml up --build
