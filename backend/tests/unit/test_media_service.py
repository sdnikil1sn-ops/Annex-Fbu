"""Unit tests for the MediaService (Phase 14)."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from app.application.ports.media import ForensicsReport
from app.application.services.media_service import MediaService
from app.infrastructure.media.mock_media_adapters import (
    MockForensicsAdapter,
    MockOcrAdapter,
)
from app.infrastructure.repositories.mock_media_repository import MockMediaRepository

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-payload"
UNKNOWN_BYTES = b"definitely not an image"


def _service(*, signals: dict | None = None) -> MediaService:
    report = ForensicsReport(
        signals=signals or {"width": 64, "height": 48, "ela_mean": 1.2},
        risk_score=0.1,
    )
    return MediaService(
        MockMediaRepository(),
        ocr_adapter=MockOcrAdapter(),
        forensics_adapter=MockForensicsAdapter(report=report),
    )


def test_ingest_persists_complete_record() -> None:
    """An image is fingerprinted, sniffed, processed, and persisted."""
    service = _service()
    analysis_id = uuid4()

    item = service.ingest(analysis_id=analysis_id, image_bytes=PNG_BYTES)

    assert item.analysis_id == analysis_id
    assert item.mime == "image/png"
    assert item.sha256 == hashlib.sha256(PNG_BYTES).hexdigest()
    assert item.size_bytes == len(PNG_BYTES)
    assert item.width == 64 and item.height == 48
    assert item.storage_path == f"inline/{item.sha256}.png"

    assert item.ocr is not None
    assert item.ocr.media_item_id == item.id
    assert item.ocr.raw_text == "mock ocr text"
    assert item.ocr.confidence == 0.9
    assert item.ocr.language == "eng"

    assert item.forensics is not None
    assert item.forensics.media_item_id == item.id
    assert item.forensics.risk_score == 0.1
    assert item.forensics.signals["width"] == 64
    assert item.forensics.model == "opencv-ela-v1"

    # The persisted copy is the one the repository returns.
    assert service.get(item.id) == item


def test_ingest_unknown_mime_uses_bin_extension() -> None:
    """Unrecognized magic bytes fall back to octet-stream + .bin path."""
    item = _service().ingest(analysis_id=uuid4(), image_bytes=UNKNOWN_BYTES)
    assert item.mime == "application/octet-stream"
    assert item.storage_path.endswith(".bin")
    # Width/height come from the forensics signals when present.
    assert item.width == 64


def test_get_missing_returns_none() -> None:
    """An unknown media id yields None, not an error."""
    assert _service().get(uuid4()) is None
