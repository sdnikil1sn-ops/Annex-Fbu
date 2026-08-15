"""Gemini vision OCR adapter (production fallback, no system binary).

The Tesseract adapter needs the ``tesseract`` binary, which Render's
native Python runtime does not install. This adapter uses the already
configured Gemini API key to extract text from an image — no system
packages required — so image analysis works on every deployment that
has a Gemini key. Tesseract remains the first choice when present.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.media import OcrAdapter, OcrResult


@dataclass
class GeminiOcrAdapter(OcrAdapter):
    """Extracts text from image bytes via the Gemini vision API."""

    client: object
    model: str = "gemini-3.1-flash-lite"

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        """Ask Gemini to transcribe the image's visible text.

        Args:
            image_bytes: Raw image data (PNG/JPEG/...).

        Returns:
            The extracted text (possibly empty when the image has no
            readable text) with no confidence estimate (API does not
            expose per-word confidence).

        Raises:
            MediaProcessingError: When the provider cannot process the
                image (raised by the caller's pipeline catch).
        """
        from google.genai import types as genai_types

        response = self.client.models.generate_content(
            model=self.model,
            contents=genai_types.Part.from_bytes(
                data=image_bytes,
                mime_type=_guess_mime(image_bytes),
            ),
            config=genai_types.GenerateContentConfig(
                system_instruction=(
                    "You are the OCR engine of ANNEX, a media-literacy "
                    "analyst. Transcribe ALL visible text from the image "
                    "exactly as written. If there is no readable text, "
                    "return an empty string."
                ),
                temperature=0,
            ),
        )
        text = (response.text or "").strip()
        return OcrResult(text=text, confidence=None, language="eng")


def _guess_mime(image_bytes: bytes) -> str:
    """Best-effort MIME from magic bytes (mirrors media_pipeline.guess_mime)."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"
