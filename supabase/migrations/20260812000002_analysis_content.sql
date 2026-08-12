-- =====================================================================
-- ANNEX — Migration 20260812000002: analysis content
-- Persists the submitted input (untrusted text) on the analyses aggregate
-- so the Celery worker can (re)process an analysis from its ID alone:
-- idempotent, resumable pipelines keyed by analysis_id (ADR-0008).
-- =====================================================================

alter table public.analyses add column if not exists content text;
