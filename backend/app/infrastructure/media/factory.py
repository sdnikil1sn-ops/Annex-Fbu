"""Composition-root factory for media adapters (OCR + forensics + pipeline)."""

from __future__ import annotations

import logging

from app.application.ports.media import (
    ForensicsAdapter,
    OcrAdapter,
    OcrResult,
)
from app.application.services.media_pipeline import MediaPipeline
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.media.mock_media_adapters import MockOcrAdapter
from app.infrastructure.media.url_fetcher import build_url_fetcher

logger = logging.getLogger(__name__)


def build_ocr_adapter(settings: Settings) -> OcrAdapter:
    """Build the Tesseract OCR adapter with honest degradation.

    A missing Tesseract binary raises ``ConfigurationError`` at construction.
    The fallback keeps the application bootable on machines without the
    binary and is logged loudly so the degradation stays observable.

    Crucially, the fallback never fabricates text: an empty OCR result
    (with an error-level log in production) is returned instead of the
    fake "mock ocr text" a naive mock would produce — image submissions
    then fail honestly ("no text found") instead of generating claims
    from invented content.

    Args:
        settings: Application settings with the OCR language codes.

    Returns:
        The Tesseract adapter, or an honest empty-result fallback when the
        binary is absent.
    """
    try:
        from app.infrastructure.media.pytesseract_ocr import TesseractOcrAdapter

        return TesseractOcrAdapter(languages=settings.ocr_languages)
    except ConfigurationError:
        if settings.app_env == "production":
            logger.error(
                "tesseract binary is not installed in this production "
                "environment — image OCR will return no text. Install "
                "tesseract-ocr (backend/apt.txt) so image analysis works."
            )
        else:
            logger.warning(
                "tesseract binary not found; OCR will return no text"
            )
        return _EmptyOcrAdapter()


class _EmptyOcrAdapter(OcrAdapter):
    """Returns an empty OCR result instead of fabricating text."""

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        return OcrResult(text="", confidence=None, language="eng")


def build_forensics_adapter() -> ForensicsAdapter:
    """Build the OpenCV forensics adapter.

    OpenCV is a Python package (no external binary), so this never needs a
    fallback. Kept as a factory for symmetry with the other composition-root
    builders and to isolate the dependency at the wiring boundary.
    """
    from app.infrastructure.media.opencv_forensics import OpenCvForensicsAdapter

    return OpenCvForensicsAdapter()


def build_media_pipeline(
    settings: Settings,
    *,
    ocr_adapter: OcrAdapter | None = None,
    forensics_adapter: ForensicsAdapter | None = None,
) -> MediaPipeline:
    """Build the media pipeline: SSRF-guarded fetch + OCR + forensics (Phase 13).

    The single construction site for the pipeline, shared by the API
    composition root and the Celery worker so both processes behave
    identically (ADR-0008). Fetch timeouts/limits come from settings; the
    OCR factory falls back to the explicit mock when the Tesseract binary
    is missing. Adapter overrides let ``create_app`` inject test doubles
    exactly like the other composition-root builders.

    Args:
        settings: Application settings with fetch and OCR configuration.
        ocr_adapter: Optional OCR adapter override (tests inject mocks).
        forensics_adapter: Optional forensics override (tests inject mocks).

    Returns:
        A wired ``MediaPipeline`` over the configured media adapters.
    """
    return MediaPipeline(
        url_fetcher=build_url_fetcher(),
        ocr_adapter=ocr_adapter or build_ocr_adapter(settings),
        forensics_adapter=forensics_adapter or build_forensics_adapter(),
        fetch_timeout=settings.media_fetch_timeout,
        fetch_max_bytes=settings.media_fetch_max_bytes,
    )
