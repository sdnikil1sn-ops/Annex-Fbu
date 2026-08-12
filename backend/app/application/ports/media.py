"""Media-processing ports: OCR and image forensics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class OcrResult:
    """Text extracted from an image."""

    text: str
    confidence: float | None = None
    language: str | None = None


@dataclass(frozen=True)
class ForensicsReport:
    """Signals computed from an image."""

    signals: dict[str, Any]
    risk_score: float


class MediaProcessingError(Exception):
    """Raised when an image cannot be decoded or processed."""


class OcrAdapter(Protocol):
    """Extracts text from image bytes."""

    def extract_text(self, image_bytes: bytes) -> OcrResult: ...


class ForensicsAdapter(Protocol):
    """Computes manipulation/tamper signals from image bytes."""

    def analyze(self, image_bytes: bytes) -> ForensicsReport: ...
