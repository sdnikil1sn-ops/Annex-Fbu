-- =====================================================================
-- ANNEX — Migration 20260814000001: community translation suggestions
-- Phase 18. Any authenticated user can propose a translation for an
-- enabled locale; moderators review and approve suggestions, and an
-- approved suggestion is published into i18n_translations (bumping its
-- version) so bundles refresh over the air (ADR-0007). The table is a
-- review queue: one open suggestion per (user, locale, key) keeps the
-- queue clean and re-suggesting idempotent.
-- =====================================================================

-- A translation suggestion awaiting (or having received) review.
create table if not exists public.translation_suggestions (
    id uuid primary key default gen_random_uuid(),
    locale_id uuid not null references public.i18n_locales (id) on delete cascade,
    namespace text not null check (char_length(namespace) between 1 and 64),
    key text not null check (char_length(key) between 1 and 128),
    value text not null check (char_length(value) between 1 and 1000),
    plural_rule text not null default 'none',
    suggested_by uuid not null references public.users (id) on delete cascade,
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected')),
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    reviewed_by uuid references public.users (id) on delete set null
);

-- One open suggestion per contributor per key; once reviewed, the same
-- user may suggest again (a new row is allowed).
create unique index if not exists idx_suggestion_open_unique
    on public.translation_suggestions (locale_id, namespace, key, suggested_by)
    where status = 'pending';

create index if not exists idx_translation_suggestions_status
    on public.translation_suggestions (status, created_at);

-- --- row-level security ------------------------------------------------
-- Defense-in-depth (ADR-0004): contributors manage their own pending
-- suggestions; moderators read the whole queue and update status. The
-- backend's service role bypasses RLS for its own writes.
alter table public.translation_suggestions enable row level security;

create policy "suggestions_insert_own" on public.translation_suggestions
    for insert with check (auth.uid() = suggested_by);
create policy "suggestions_select_own" on public.translation_suggestions
    for select using (
        auth.uid() = suggested_by
        or exists (
            select 1 from public.profiles p
            where p.user_id = auth.uid() and p.role in ('moderator', 'admin')
        )
    );
create policy "suggestions_update_own_pending" on public.translation_suggestions
    for update using (auth.uid() = suggested_by and status = 'pending');
create policy "suggestions_update_moderator" on public.translation_suggestions
    for update using (
        exists (
            select 1 from public.profiles p
            where p.user_id = auth.uid() and p.role in ('moderator', 'admin')
        )
    );
