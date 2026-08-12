# =====================================================================
# ANNEX — local dev stack (Phase 7)
# Starts Redis, the FastAPI service, and the Celery analysis worker via
# the docker compose dev stack. Idempotent: safe to re-run.
# =====================================================================
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

# DATABASE_URL is required by the backend container (compose fails loudly
# when unset). Local Supabase default is used when not provided.
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql://postgres:postgres@host.docker.internal:54322/postgres"
}

docker compose -f docker/compose.dev.yml up --build
