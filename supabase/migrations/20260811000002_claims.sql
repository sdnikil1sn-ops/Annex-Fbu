-- =====================================================================
-- ANNEX — Migration 20260811000002: claims context
-- Claims extracted from an analysis, their verdicts, and evidence.
-- =====================================================================

-- A claim extracted from the analysis input.
create table if not exists public.claims (
    id uuid primary key default gen_random_uuid(),
    analysis_id uuid not null references public.analyses (id) on delete cascade,
    claim_index int not null,
    text text not null,
    normalized_text text,
    unique (analysis_id, claim_index)
);

-- Verdict per claim, with model provenance.
create table if not exists public.claim_verdicts (
    id uuid primary key default gen_random_uuid(),
    claim_id uuid not null references public.claims (id) on delete cascade,
    verdict text not null check (
        verdict in (
            'verifiable',
            'partially_verifiable',
            'unverifiable',
            'true',
            'false',
            'misleading'
        )
    ),
    confidence numeric(3, 2) not null check (confidence >= 0 and confidence <= 1),
    model text,
    model_version text,
    rationale text,
    created_at timestamptz not null default now()
);

-- Evidence supporting a verdict.
create table if not exists public.evidence (
    id uuid primary key default gen_random_uuid(),
    verdict_id uuid not null references public.claim_verdicts (id) on delete cascade,
    kind text not null check (kind in ('link', 'quote', 'source')),
    url text,
    quote text,
    snippet text,
    relevance numeric(3, 2) check (relevance >= 0 and relevance <= 1)
);
