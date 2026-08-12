"""Media service — ingests images and persists OCR + forensics (Phase 14).

An ingested image is fingerprinted (SHA-256), sniffed for its MIME type,
and run through the bound OCR + forensics adapters; the resulting
``MediaItem`` aggregate (with its ``OcrRecord`` and ``ForensicsRecord``
children) is persisted by the repository. The image bytes themselves are
not stored — the ``storage_path`` placeholder points at the object-store
key once storage is wired (Phase 11 deployment topology reserves it).
"""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from app.application.ports.media import ForensicsAdapter, OcrAdapter
from app.application.ports.repositories import MediaRepository
from app.application.services.media_pipeline import guess_mime
from app.domain.media import ForensicsRecord, MediaItem, OcrRecord

# File extension per sniffed MIME for the inline storage path.
_MIME_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
}

# Attributed forensics model (the OpenCV ELA adapter, see opencv_forensics).
_FORENSICS_MODEL = "opencv-ela-v1"


class MediaService:
    """Ingests an image and persists its media record with children."""

    def __init__(
        self,
        repository: MediaRepository,
        *,
        ocr_adapter: OcrAdapter,
        forensics_adapter: ForensicsAdapter,
    ) -> None:
        self._repository = repository
        self._ocr = ocr_adapter
        self._forensics = forensics_adapter

    def ingest(self, *, analysis_id: UUID, image_bytes: bytes) -> MediaItem:
        """Process and persist one image, returning its media record.

        Args:
            analysis_id: The analysis this media belongs to.
            image_bytes: The raw image bytes (already validated/decoded).

        Returns:
            The persisted media item with OCR + forensics attached.

        Raises:
            MediaProcessingError: When the image cannot be processed.
        """
        sha256 = hashlib.sha256(image_bytes).hexdigest()
        mime = guess_mime(image_bytes)
        ocr = self._ocr.extract_text(image_bytes)
        forensics = self._forensics.analyze(image_bytes)

        item_id = uuid4()
        item = MediaItem(
            id=item_id,
            analysis_id=analysis_id,
            storage_path=f"inline/{sha256}.{_MIME_EXTENSIONS.get(mime, 'bin')}",
            mime=mime,
            sha256=sha256,
            width=forensics.signals.get("width"),
            height=forensics.signals.get("height"),
            size_bytes=len(image_bytes),
            ocr=OcrRecord(
                media_item_id=item_id,
                language=ocr.language,
                confidence=ocr.confidence,
                raw_text=ocr.text,
            ),
            forensics=ForensicsRecord(
                media_item_id=item_id,
                signals=forensics.signals,
                risk_score=forensics.risk_score,
                model=_FORENSICS_MODEL,
            ),
        )
        return self._repository.save(item)

    def get(self, media_id: UUID) -> MediaItem | None:
        """Fetch one media record with its OCR + forensics children."""
        return self._repository.get(media_id)
