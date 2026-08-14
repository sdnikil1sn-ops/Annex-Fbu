-- =====================================================================
-- ANNEX — Migration 20260815000001: source credibility feedback
-- Phase 19. The public source registry grows more accurate the more it
-- is used: authenticated users rate a source's credibility (1–5), and
-- the profile aggregates the community signal (count + average) next to
-- the model score. One rating per (source, user) — re-rating updates
-- the row, so each user contributes exactly one voice.
-- =====================================================================

-- Community credibility ratings for a source.
create table if not exists public.source_feedback (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null references public.sources (id) on delete cascade,
    user_id uuid not null references public.users (id) on delete cascade,
    rating int not null check (rating >= 1 and rating <= 5),
    created_at timestamptz not null default now(),
    unique (source_id, user_id)
);

create index if not exists idx_source_feedback_source
    on public.source_feedback (source_id);

-- --- row-level security ------------------------------------------------
-- Defense-in-depth (ADR-0004): users manage only their own ratings; the
-- service role (backend) reads the aggregate and bypasses RLS for its
-- own writes.
alter table public.source_feedback enable row level security;

create policy "source_feedback_insert_own" on public.source_feedback
    for insert with check (auth.uid() = user_id);
create policy "source_feedback_select_own" on public.source_feedback
    for select using (auth.uid() = user_id);
create policy "source_feedback_update_own" on public.source_feedback
    for update using (auth.uid() = user_id);
create policy "source_feedback_delete_own" on public.source_feedback
    for delete using (auth.uid() = user_id);
