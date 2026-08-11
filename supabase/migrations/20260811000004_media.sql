-- =====================================================================
-- ANNEX — Migration 20260811000004: media context
-- Uploaded media, OCR results, and image-forensics reports.
-- =====================================================================

-- Media attached to an analysis (stored in Supabase Storage).
create table if not exists public.media_items (
    id uuid primary key default gen_random_uuid(),
    analysis_id uuid not null references public.analyses (id) on delete cascade,
    storage_path text not null,
    mime text,
    sha256 text,
    width int,
    height int,
    size_bytes bigint,
    ingested_at timestamptz not null default now()
);

-- Tesseract OCR output for a media item.
create table if not exists public.ocr_results (
    id uuid primary key default gen_random_uuid(),
    media_item_id uuid not null references public.media_items (id) on delete cascade,
    language text,
    confidence numeric(3, 2),
    raw_text text,
    boxes jsonb,
    created_at timestamptz not null default now()
);

-- OpenCV-based tamper/manipulation signals.
create table if not exists public.forensics_reports (
    id uuid primary key default gen_random_uuid(),
    media_item_id uuid not null references public.media_items (id) on delete cascade,
    signals jsonb,
    risk_score numeric(3, 2),
    model text,
    created_at timestamptz not null default now()
);
