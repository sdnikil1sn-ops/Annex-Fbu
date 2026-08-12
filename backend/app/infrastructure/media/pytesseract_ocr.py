"""OCR via Tesseract (pytesseract wrapper)."""

from __future__ import annotations

from app.application.ports.media import OcrAdapter, OcrResult
from app.core.exceptions import ConfigurationError
from app.infrastructure.media.utils import decode_image


class TesseractOcrAdapter(OcrAdapter):
    """Extracts text from images using the Tesseract binary.

    Args:
        languages: Tesseract language codes, e.g. ``"eng"`` or ``"eng+spa"``.

    Raises:
        ConfigurationError: When the tesseract binary is not installed.
    """

    def __init__(self, languages: str = "eng") -> None:
        import pytesseract

        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError as exc:
            raise ConfigurationError(
                "tesseract binary not found on PATH — install Tesseract OCR "
                "and ensure it is reachable from the worker environment"
            ) from exc
        self._tesseract = pytesseract
        self._languages = languages

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        """Run OCR over the decoded image.

        Args:
            image_bytes: Raw image data.

        Returns:
            The extracted text with a mean confidence score.

        Raises:
            MediaProcessingError: When the image cannot be decoded.
        """
        image = decode_image(image_bytes)
        data = self._tesseract.image_to_data(
            image,
            lang=self._languages,
            output_type=self._tesseract.Output.DICT,
        )
        words = [
            data["text"][index] for index in range(len(data["text"])) if data["conf"][index] != "-1"
        ]
        confidences = [
            float(data["conf"][index])
            for index in range(len(data["conf"]))
            if data["conf"][index] != "-1"
        ]
        text = " ".join(word for word in words if word.strip())
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OcrResult(
            text=text.strip(),
            confidence=confidence,
            language=self._languages,
        )
