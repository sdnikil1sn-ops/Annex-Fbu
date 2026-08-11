-- =====================================================================
-- ANNEX — Migration 20260811000006: row-level security
-- RLS is defense-in-depth (ADR-0004): even a buggy application query can
-- never read rows outside the caller's ownership. Ownership is keyed on
-- auth.uid() = the Firebase UID mirrored in users.id (ADR-0005).
-- The service role bypasses RLS for worker/batch operations.
-- =====================================================================

alter table public.users enable row level security;
alter table public.profiles enable row level security;
alter table public.user_preferences enable row level security;
alter table public.analyses enable row level security;
alter table public.analysis_scores enable row level security;
alter table public.claims enable row level security;
alter table public.claim_verdicts enable row level security;
alter table public.evidence enable row level security;
alter table public.sources enable row level security;
alter table public.source_scores enable row level security;
alter table public.media_items enable row level security;
alter table public.ocr_results enable row level security;
alter table public.forensics_reports enable row level security;
alter table public.i18n_locales enable row level security;
alter table public.i18n_translations enable row level security;

-- --- users / profiles / preferences: owner only ----------------------

create policy "users_select_own" on public.users
    for select using (auth.uid() = id);
create policy "users_update_own" on public.users
    for update using (auth.uid() = id);

create policy "profiles_select_own" on public.profiles
    for select using (auth.uid() = user_id);
create policy "profiles_update_own" on public.profiles
    for update using (auth.uid() = user_id);

create policy "user_preferences_select_own" on public.user_preferences
    for select using (auth.uid() = user_id);
create policy "user_preferences_update_own" on public.user_preferences
    for update using (auth.uid() = user_id);

-- --- analyses: owner only (anonymous rows have no owner) --------------

create policy "analyses_insert_own" on public.analyses
    for insert with check (auth.uid() = user_id);
create policy "analyses_select_own" on public.analyses
    for select using (auth.uid() = user_id);
create policy "analyses_update_own" on public.analyses
    for update using (auth.uid() = user_id);
create policy "analyses_delete_own" on public.analyses
    for delete using (auth.uid() = user_id);

-- --- derived analysis tables: owner via their analysis ----------------

create policy "analysis_scores_select_own" on public.analysis_scores
    for select using (
        exists (
            select 1 from public.analyses a
            where a.id = analysis_id and a.user_id = auth.uid()
        )
    );

create policy "claims_select_own" on public.claims
    for select using (
        exists (
            select 1 from public.analyses a
            where a.id = analysis_id and a.user_id = auth.uid()
        )
    );

create policy "claim_verdicts_select_own" on public.claim_verdicts
    for select using (
        exists (
            select 1 from public.claims c
            join public.analyses a on a.id = c.analysis_id
            where c.id = claim_id and a.user_id = auth.uid()
        )
    );

create policy "evidence_select_own" on public.evidence
    for select using (
        exists (
            select 1 from public.claim_verdicts v
            join public.claims c on c.id = v.claim_id
            join public.analyses a on a.id = c.analysis_id
            where v.id = verdict_id and a.user_id = auth.uid()
        )
    );

create policy "media_items_select_own" on public.media_items
    for select using (
        exists (
            select 1 from public.analyses a
            where a.id = analysis_id and a.user_id = auth.uid()
        )
    );

create policy "ocr_results_select_own" on public.ocr_results
    for select using (
        exists (
            select 1 from public.media_items m
            join public.analyses a on a.id = m.analysis_id
            where m.id = media_item_id and a.user_id = auth.uid()
        )
    );

create policy "forensics_reports_select_own" on public.forensics_reports
    for select using (
        exists (
            select 1 from public.media_items m
            join public.analyses a on a.id = m.analysis_id
            where m.id = media_item_id and a.user_id = auth.uid()
        )
    );

-- --- public-reference data: readable by everyone -----------------------

create policy "sources_public_read" on public.sources
    for select using (true);
create policy "source_scores_public_read" on public.source_scores
    for select using (true);
create policy "i18n_locales_public_read" on public.i18n_locales
    for select using (true);
create policy "i18n_translations_public_read" on public.i18n_translations
    for select using (true);
