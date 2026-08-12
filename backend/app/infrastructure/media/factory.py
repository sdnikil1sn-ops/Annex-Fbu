"""Composition-root factory for media adapters (OCR + forensics)."""

from __future__ import annotations

import logging

from app.application.ports.media import ForensicsAdapter, OcrAdapter
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.media.mock_media_adapters import MockOcrAdapter

logger = logging.getLogger(__name__)


def build_ocr_adapter(settings: Settings) -> OcrAdapter:
    """Build the Tesseract OCR adapter, falling back to the explicit mock.

    A missing Tesseract binary raises ``ConfigurationError`` at construction;
    the fallback keeps the application bootable on machines without the
    binary (local development) and is logged as a warning so the degradation
    stays observable where real OCR is expected.

    Args:
        settings: Application settings with the OCR language codes.

    Returns:
        The Tesseract adapter, or the explicit mock when the binary is absent.
    """
    try:
        from app.infrastructure.media.pytesseract_ocr import TesseractOcrAdapter

        return TesseractOcrAdapter(languages=settings.ocr_languages)
    except ConfigurationError:
        logger.warning(
            "tesseract binary not found; falling back to the mock OCR adapter"
        )
        return MockOcrAdapter()


def build_forensics_adapter() -> ForensicsAdapter:
    """Build the OpenCV forensics adapter.

    OpenCV is a Python package (no external binary), so this never needs a
    fallback. Kept as a factory for symmetry with the other composition-root
    builders and to isolate the dependency at the wiring boundary.
    """
    from app.infrastructure.media.opencv_forensics import OpenCvForensicsAdapter

    return OpenCvForensicsAdapter()
