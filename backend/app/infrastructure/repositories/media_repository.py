"""PostgreSQL implementation of the MediaRepository port (Phase 14).

Persists the media item and its OCR + forensics children; reads assemble
the aggregate with its latest children attached. Every query is
parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.application.ports.repositories import MediaRepository
from app.domain.media import ForensicsRecord, MediaItem, OcrRecord


class PostgresMediaRepository(MediaRepository):
    """MediaRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def save(self, item: MediaItem) -> MediaItem:
        """Insert the media item and its OCR/forensics children."""
        with self._connect() as conn:
            conn.execute(
                """
                insert into public.media_items
                    (id, analysis_id, storage_path, mime, sha256, width, height,
                     size_bytes, ingested_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item.id,
                    item.analysis_id,
                    item.storage_path,
                    item.mime,
                    item.sha256,
                    item.width,
                    item.height,
                    item.size_bytes,
                    item.ingested_at,
                ),
            )
            if item.ocr is not None:
                conn.execute(
                    """
                    insert into public.ocr_results
                        (id, media_item_id, language, confidence, raw_text, boxes)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item.ocr.id,
                        item.ocr.media_item_id,
                        item.ocr.language,
                        item.ocr.confidence,
                        item.ocr.raw_text,
                        Jsonb(item.ocr.boxes) if item.ocr.boxes is not None else None,
                    ),
                )
            if item.forensics is not None:
                conn.execute(
                    """
                    insert into public.forensics_reports
                        (id, media_item_id, signals, risk_score, model)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        item.forensics.id,
                        item.forensics.media_item_id,
                        Jsonb(item.forensics.signals),
                        item.forensics.risk_score,
                        item.forensics.model,
                    ),
                )
        return item

    def get(self, media_id: UUID) -> MediaItem | None:
        """Fetch one media item with its latest OCR + forensics children."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select id, analysis_id, storage_path, mime, sha256, width, height,
                       size_bytes, ingested_at
                from public.media_items
                where id = %s
                """,
                (media_id,),
            ).fetchone()
            if row is None:
                return None
            ocr_row = conn.execute(
                """
                select id, media_item_id, language, confidence, raw_text, boxes
                from public.ocr_results
                where media_item_id = %s
                order by created_at desc
                limit 1
                """,
                (media_id,),
            ).fetchone()
            forensics_row = conn.execute(
                """
                select id, media_item_id, signals, risk_score, model
                from public.forensics_reports
                where media_item_id = %s
                order by created_at desc
                limit 1
                """,
                (media_id,),
            ).fetchone()
        ocr = (
            OcrRecord(
                id=ocr_row["id"],
                media_item_id=ocr_row["media_item_id"],
                language=ocr_row["language"],
                confidence=ocr_row["confidence"],
                raw_text=ocr_row["raw_text"],
                boxes=ocr_row["boxes"],
            )
            if ocr_row
            else None
        )
        forensics = (
            ForensicsRecord(
                id=forensics_row["id"],
                media_item_id=forensics_row["media_item_id"],
                signals=forensics_row["signals"],
                risk_score=forensics_row["risk_score"],
                model=forensics_row["model"],
            )
            if forensics_row
            else None
        )
        return MediaItem(
            id=row["id"],
            analysis_id=row["analysis_id"],
            storage_path=row["storage_path"],
            mime=row["mime"],
            sha256=row["sha256"],
            width=row["width"],
            height=row["height"],
            size_bytes=row["size_bytes"],
            ingested_at=row["ingested_at"],
            ocr=ocr,
            forensics=forensics,
        )
