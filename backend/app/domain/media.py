"""Media aggregate — uploaded images with OCR + forensics (Phase 14).

Persisted into ``media_items`` / ``ocr_results`` / ``forensics_reports``
when an image is ingested through the media service. The aggregate carries
its OCR and forensics children so the API can render a complete media
record in one read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class OcrRecord:
    """OCR output for a media item."""

    media_item_id: UUID
    id: UUID = field(default_factory=uuid4)
    language: str | None = None
    confidence: float | None = None
    raw_text: str | None = None
    boxes: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ForensicsRecord:
    """Image-forensics signals for a media item."""

    media_item_id: UUID
    signals: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    risk_score: float = 0.0
    model: str | None = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class MediaItem:
    """A persisted media item with its OCR + forensics children."""

    analysis_id: UUID
    storage_path: str
    id: UUID = field(default_factory=uuid4)
    mime: str | None = None
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None
    ingested_at: datetime = field(default_factory=_utcnow)
    ocr: OcrRecord | None = None
    forensics: ForensicsRecord | None = None
