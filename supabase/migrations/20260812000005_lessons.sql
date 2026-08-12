-- =====================================================================
-- ANNEX — Migration 20260812000005: education lessons
-- The media-literacy curriculum (Phase 15): lesson metadata, localized
-- content (per enabled locale, falling back through the i18n chain —
-- ADR-0007), and per-user completion progress. Lessons/content are
-- public-read reference data (the API layer decides authentication);
-- progress is strictly owner-scoped.
-- =====================================================================

-- Lesson metadata. Content lives in lesson_contents; this row is
-- locale-independent.
create table if not exists public.lessons (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    difficulty text not null default 'beginner'
        check (difficulty in ('beginner', 'intermediate', 'advanced')),
    category text not null default 'media_literacy',
    estimated_minutes int not null default 5
        check (estimated_minutes between 1 and 120),
    order_index int not null default 0,
    published boolean not null default false,
    created_at timestamptz not null default now()
);

-- Localized lesson content, keyed by locale like i18n_translations. A
-- lesson without a row for the requested locale resolves through the
-- fallback chain (requested → parent → … → default) in the repository.
create table if not exists public.lesson_contents (
    id uuid primary key default gen_random_uuid(),
    lesson_id uuid not null references public.lessons (id) on delete cascade,
    locale_id uuid not null references public.i18n_locales (id) on delete cascade,
    title text not null,
    summary text not null,
    sections jsonb not null default '[]',
    updated_at timestamptz not null default now(),
    unique (lesson_id, locale_id)
);

-- Per-user completion. Idempotent: one row per (user, lesson).
create table if not exists public.lesson_progress (
    user_id uuid not null references public.users (id) on delete cascade,
    lesson_id uuid not null references public.lessons (id) on delete cascade,
    completed_at timestamptz not null default now(),
    primary key (user_id, lesson_id)
);

-- --- row-level security ------------------------------------------------

alter table public.lessons enable row level security;
alter table public.lesson_contents enable row level security;
alter table public.lesson_progress enable row level security;

create policy "lessons_public_read" on public.lessons
    for select using (true);
create policy "lesson_contents_public_read" on public.lesson_contents
    for select using (true);

create policy "lesson_progress_select_own" on public.lesson_progress
    for select using (auth.uid() = user_id);
create policy "lesson_progress_insert_own" on public.lesson_progress
    for insert with check (auth.uid() = user_id);
create policy "lesson_progress_delete_own" on public.lesson_progress
    for delete using (auth.uid() = user_id);
