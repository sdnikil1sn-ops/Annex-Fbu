-- =====================================================================
-- ANNEX — Migration 20260811000005: i18n context
-- Runtime translation delivery (ADR-0007): adding a language is a
-- data change, never a rebuild.
-- =====================================================================

-- Enabled locales with their fallback chain.
create table if not exists public.i18n_locales (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,
    enabled boolean not null default true,
    fallback_code text
);

-- Versioned translation entries per locale/namespace/key.
create table if not exists public.i18n_translations (
    id uuid primary key default gen_random_uuid(),
    locale_id uuid not null references public.i18n_locales (id) on delete cascade,
    namespace text not null,
    key text not null,
    value text not null,
    plural_rule text not null default 'none',
    version int not null default 1,
    updated_at timestamptz not null default now(),
    unique (locale_id, namespace, key)
);
