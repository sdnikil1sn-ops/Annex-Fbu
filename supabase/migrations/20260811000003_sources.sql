-- =====================================================================
-- ANNEX — Migration 20260811000003: sources context
-- Publisher/domain registry and credibility scores.
-- =====================================================================

-- Canonical publisher/domain registry.
create table if not exists public.sources (
    id uuid primary key default gen_random_uuid(),
    domain text not null unique,
    name text,
    country text,
    language text,
    category text,
    first_seen_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Explainable credibility score with named trust signals.
create table if not exists public.source_scores (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null references public.sources (id) on delete cascade,
    score numeric(3, 2) not null check (score >= 0 and score <= 1),
    signals jsonb,
    model text,
    computed_at timestamptz not null default now()
);
