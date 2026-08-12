-- =====================================================================
-- ANNEX — Migration 20260812000001: analysis report
-- Stores the claim-analysis output (claims + summary) as JSONB on the
-- analyses aggregate so clients can fetch the report by analysis ID
-- (Phase 6 analysis API).
-- =====================================================================

alter table public.analyses add column if not exists report jsonb;
