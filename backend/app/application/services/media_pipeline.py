"""Media pipeline — extraction stage of the analysis pipeline (Phase 13).

Turns a submitted URL or image into the text the claim analyzer consumes,
plus the media context that ships with the report:

- ``url``  → SSRF-guarded fetch + HTML text extraction (``UrlFetcher``);
- ``image`` → OCR (``OcrAdapter``) + tamper forensics (``ForensicsAdapter``),
  with the extracted text fed to the analyzer and the signals persisted.

The pipeline is application-layer glue over the media ports: the service
(and the Celery worker) depend on this class, never on the infrastructure
adapters directly (ADR-0003). All dependencies are injectable, so tests
use the explicit mocks.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any

from app.application.ports.media import (
    ForensicsAdapter,
    MediaProcessingError,
    OcrAdapter,
    UrlFetcher,
)
from app.domain.analysis import Analysis, AnalysisInputType


class MediaPipeline:
    """Extracts analyzable text and media context from an analysis input."""

    def __init__(
        self,
        *,
        url_fetcher: UrlFetcher,
        ocr_adapter: OcrAdapter,
        forensics_adapter: ForensicsAdapter,
        fetch_timeout: float = 10.0,
        fetch_max_bytes: int = 2_000_000,
    ) -> None:
        self._url_fetcher = url_fetcher
        self._ocr = ocr_adapter
        self._forensics = forensics_adapter
        self._fetch_timeout = fetch_timeout
        self._fetch_max_bytes = fetch_max_bytes

    def extract(self, analysis: Analysis) -> tuple[str, dict[str, Any] | None]:
        """Return ``(text_to_analyze, media_context)`` for any input type.

        Text passes through untouched with no media context. URL inputs are
        fetched and extracted; image inputs run OCR + forensics.

        Args:
            analysis: A submitted (non-terminal) analysis.

        Returns:
            The text to hand to the claim analyzer and an optional media
            context object merged into the persisted report.

        Raises:
            UrlFetchError: The URL could not be fetched safely.
            MediaProcessingError: The image could not be decoded/processed.
        """
        if analysis.input_type is AnalysisInputType.TEXT:
            return analysis.content or "", None
        if analysis.input_type is AnalysisInputType.URL:
            return self._extract_url(analysis)
        if analysis.input_type is AnalysisInputType.IMAGE:
            return self._extract_image(analysis)
        raise MediaProcessingError(f"unsupported input type: {analysis.input_type}")

    def _extract_url(self, analysis: Analysis) -> tuple[str, dict[str, Any]]:
        url = analysis.content or ""
        page = self._url_fetcher.fetch(
            url,
            timeout=self._fetch_timeout,
            max_bytes=self._fetch_max_bytes,
        )
        context = {
            "input": {
                "type": "url",
                "url": url,
                "final_url": page.final_url,
                "status": page.status,
            }
        }
        return page.text, context

    def _extract_image(self, analysis: Analysis) -> tuple[str, dict[str, Any]]:
        try:
            image_bytes = base64.b64decode(analysis.content or "", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise MediaProcessingError("image payload is not valid base64") from exc
        if not image_bytes:
            raise MediaProcessingError("image payload is empty")

        ocr_result = self._ocr.extract_text(image_bytes)
        forensics = self._forensics.analyze(image_bytes)
        context = {
            "input": {
                "type": "image",
                "mime": _guess_mime(image_bytes),
                "size_bytes": len(image_bytes),
            },
            "ocr": {
                "text": ocr_result.text,
                "confidence": ocr_result.confidence,
            },
            "forensics": {
                "risk_score": forensics.risk_score,
                "signals": forensics.signals,
            },
        }
        return ocr_result.text, context


def _guess_mime(image_bytes: bytes) -> str:
    """Sniff a small MIME type from the image magic bytes (best effort)."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"
