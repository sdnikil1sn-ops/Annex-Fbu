-- =====================================================================
-- ANNEX — Migration 20260811000001: core tables
-- Identity (users/profiles/preferences) and the analyses aggregate.
-- Logical design: docs/database/schema-design.md
-- =====================================================================

-- Users mirror Firebase identities; id = Firebase UID (ADR-0005).
create table if not exists public.users (
    id uuid primary key,
    email text unique,
    display_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    last_seen_at timestamptz
);

-- One-to-one profile carrying role and consent.
create table if not exists public.profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references public.users (id) on delete cascade,
    role text not null default 'user' check (role in ('user', 'moderator', 'admin')),
    locale text not null default 'en',
    country text,
    consent_flags jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

-- Per-user preferences.
create table if not exists public.user_preferences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references public.users (id) on delete cascade,
    default_locale text not null default 'en',
    theme text not null default 'system' check (theme in ('system', 'light', 'dark')),
    notifications jsonb not null default '{}'::jsonb
);

-- Analyses: the core aggregate (state machine per ADR-0008).
create table if not exists public.analyses (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.users (id) on delete set null,
    input_type text not null check (input_type in ('text', 'url', 'image')),
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed', 'failed')),
    locale text not null default 'en',
    failure_reason text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_analyses_user_created
    on public.analyses (user_id, created_at desc);
create index if not exists idx_analyses_status
    on public.analyses (status);

-- Dimensional score breakdown of an analysis.
create table if not exists public.analysis_scores (
    id uuid primary key default gen_random_uuid(),
    analysis_id uuid not null references public.analyses (id) on delete cascade,
    dimension text not null,
    score numeric(3, 2) not null check (score >= 0 and score <= 1),
    breakdown jsonb,
    unique (analysis_id, dimension)
);
