"""Media endpoints — v1 contract (Phase 14).

``POST /media`` ingests an image (base64 or ``data:`` URL) for an
analysis the caller owns, runs OCR + forensics, and persists the media
record. ``GET /media/{id}`` returns the record with its children. Reads
are owner-scoped through the analysis the media belongs to.
"""

from __future__ import annotations

import base64
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import (
    get_analysis_service_dep,
    get_current_user,
    get_media_service_dep,
    get_settings_dep,
)
from app.api.errors import AppError
from app.api.v1.analysis import normalize_image
from app.application.services.analysis_service import AnalysisService
from app.application.services.media_service import MediaService
from app.core.config import Settings
from app.domain.media import MediaItem
from app.domain.user import User

router = APIRouter(prefix="/media", tags=["media"])


class SubmitMediaRequest(BaseModel):
    """Body for ``POST /media``."""

    analysis_id: UUID
    image: str


def _media_payload(item: MediaItem) -> dict[str, Any]:
    ocr = item.ocr
    forensics = item.forensics
    return {
        "id": str(item.id),
        "analysis_id": str(item.analysis_id),
        "storage_path": item.storage_path,
        "mime": item.mime,
        "sha256": item.sha256,
        "width": item.width,
        "height": item.height,
        "size_bytes": item.size_bytes,
        "ingested_at": item.ingested_at.isoformat(),
        "ocr": {
            "language": ocr.language if ocr else None,
            "confidence": ocr.confidence if ocr else None,
            "raw_text": ocr.raw_text if ocr else None,
        }
        if ocr
        else None,
        "forensics": {
            "risk_score": forensics.risk_score if forensics else None,
            "signals": forensics.signals if forensics else None,
            "model": forensics.model if forensics else None,
        }
        if forensics
        else None,
    }


@router.post("", status_code=201)
def submit_media(
    body: SubmitMediaRequest,
    user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service_dep),
    media_service: MediaService = Depends(get_media_service_dep),
    settings: Settings = Depends(get_settings_dep),
) -> dict[str, Any]:
    """Ingest an image for an owned analysis; returns the media record."""
    analysis = analysis_service.get(body.analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise AppError(
            "media.analysis_not_found",
            "The analysis does not exist or is not yours.",
            status_code=404,
        )
    encoded = normalize_image(body.image, settings.media_image_max_bytes)
    item = media_service.ingest(
        analysis_id=analysis.analysis_id,
        image_bytes=base64.b64decode(encoded),
    )
    return {"data": _media_payload(item)}


@router.get("/{media_id}")
def get_media(
    media_id: UUID,
    user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service_dep),
    media_service: MediaService = Depends(get_media_service_dep),
) -> dict[str, Any]:
    """Fetch one media record with OCR + forensics (owner only)."""
    item = media_service.get(media_id)
    if item is None:
        raise AppError("media.not_found", "Media not found.", status_code=404)
    analysis = analysis_service.get(item.analysis_id)
    if analysis is None or analysis.user_id != user.id:
        # Do not reveal whether the media exists.
        raise AppError("media.not_found", "Media not found.", status_code=404)
    return {"data": _media_payload(item)}
