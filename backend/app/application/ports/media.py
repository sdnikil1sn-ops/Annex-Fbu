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


@dataclass(frozen=True)
class FetchedPage:
    """A successfully fetched and extracted web page."""

    final_url: str
    status: int
    text: str


class UrlFetchError(Exception):
    """Raised when a URL cannot be fetched safely (SSRF guard, timeout, ...)."""


class UrlFetcher(Protocol):
    """Fetches a URL and extracts its readable text.

    Implementations MUST refuse private/loopback/link-local targets
    (SSRF guard) and cap response size and redirects.
    """

    def fetch(
        self,
        url: str,
        *,
        timeout: float = 10.0,
        max_bytes: int = 2_000_000,
    ) -> FetchedPage: ...


class OcrAdapter(Protocol):
    """Extracts text from image bytes."""

    def extract_text(self, image_bytes: bytes) -> OcrResult: ...


class ForensicsAdapter(Protocol):
    """Computes manipulation/tamper signals from image bytes."""

    def analyze(self, image_bytes: bytes) -> ForensicsReport: ...
