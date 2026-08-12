"""Tests for the MediaPipeline extraction stage (Phase 13).

The pipeline is exercised with deterministic fakes for the media ports so
every branch (text passthrough, URL extraction, image OCR + forensics, and
the failure paths) is covered without real network or image tooling.
"""

from __future__ import annotations

import base64

import pytest
from app.application.ports.media import (
    FetchedPage,
    ForensicsReport,
    MediaProcessingError,
    OcrResult,
    UrlFetchError,
)
from app.application.services.media_pipeline import MediaPipeline, _guess_mime
from app.domain.analysis import Analysis, AnalysisInputType

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-payload"
JPEG_BYTES = b"\xff\xd8\xff" + b"fake-jpeg-payload"


class FakeUrlFetcher:
    """Records calls and returns a fixed page or raises a fixed error."""

    def __init__(
        self,
        page: FetchedPage | None = None,
        error: Exception | None = None,
    ) -> None:
        self.page = page or FetchedPage(
            final_url="https://example.com/final",
            status=200,
            text="page text",
        )
        self.error = error
        self.calls: list[tuple[str, float, int]] = []

    def fetch(
        self,
        url: str,
        *,
        timeout: float = 10.0,
        max_bytes: int = 2_000_000,
    ) -> FetchedPage:
        self.calls.append((url, timeout, max_bytes))
        if self.error is not None:
            raise self.error
        return self.page


class FakeOcr:
    """Records calls and returns a fixed OCR result."""

    def __init__(self, result: OcrResult | None = None, error: Exception | None = None) -> None:
        self.result = result or OcrResult(text="ocr text", confidence=0.85, language="eng")
        self.error = error
        self.calls = 0

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class FakeForensics:
    """Records calls and returns a fixed forensics report."""

    def __init__(
        self,
        report: ForensicsReport | None = None,
        error: Exception | None = None,
    ) -> None:
        self.report = report or ForensicsReport(signals={"ela": "low"}, risk_score=0.1)
        self.error = error
        self.calls = 0

    def analyze(self, image_bytes: bytes) -> ForensicsReport:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.report


def _pipeline(
    *,
    fetcher: FakeUrlFetcher | None = None,
    ocr: FakeOcr | None = None,
    forensics: FakeForensics | None = None,
) -> tuple[MediaPipeline, FakeUrlFetcher, FakeOcr, FakeForensics]:
    f, o, fo = fetcher or FakeUrlFetcher(), ocr or FakeOcr(), forensics or FakeForensics()
    return MediaPipeline(url_fetcher=f, ocr_adapter=o, forensics_adapter=fo), f, o, fo


def test_text_input_passes_through_without_media() -> None:
    """Text content is returned untouched with no media context."""
    pipeline, fetcher, ocr, forensics = _pipeline()
    analysis = Analysis(input_type=AnalysisInputType.TEXT, content="hello world")

    text, media = pipeline.extract(analysis)

    assert text == "hello world"
    assert media is None
    assert fetcher.calls == [] and ocr.calls == 0 and forensics.calls == 0


def test_url_input_fetches_and_builds_context() -> None:
    """URL inputs are fetched and their fetch metadata becomes the context."""
    pipeline, fetcher, _, _ = _pipeline()
    analysis = Analysis(
        input_type=AnalysisInputType.URL, content="https://example.com/article"
    )

    text, media = pipeline.extract(analysis)

    assert text == "page text"
    assert media == {
        "input": {
            "type": "url",
            "url": "https://example.com/article",
            "final_url": "https://example.com/final",
            "status": 200,
        }
    }
    assert fetcher.calls == [("https://example.com/article", 10.0, 2_000_000)]


def test_image_input_runs_ocr_and_forensics() -> None:
    """Image inputs decode base64 and run both adapters, with a MIME sniff."""
    pipeline, _, ocr, forensics = _pipeline()
    analysis = Analysis(
        input_type=AnalysisInputType.IMAGE,
        content=base64.b64encode(PNG_BYTES).decode(),
    )

    text, media = pipeline.extract(analysis)

    assert text == "ocr text"
    assert media == {
        "input": {"type": "image", "mime": "image/png", "size_bytes": len(PNG_BYTES)},
        "ocr": {"text": "ocr text", "confidence": 0.85},
        "forensics": {"risk_score": 0.1, "signals": {"ela": "low"}},
    }
    assert ocr.calls == 1 and forensics.calls == 1


def test_image_input_propagates_ocr_failure() -> None:
    """An adapter failure surfaces as MediaProcessingError."""
    pipeline, _, _, _ = _pipeline(ocr=FakeOcr(error=MediaProcessingError("cannot decode")))
    analysis = Analysis(
        input_type=AnalysisInputType.IMAGE,
        content=base64.b64encode(PNG_BYTES).decode(),
    )

    with pytest.raises(MediaProcessingError, match="cannot decode"):
        pipeline.extract(analysis)


def test_image_input_rejects_invalid_base64() -> None:
    """Undecodable base64 payloads are rejected without touching the adapters."""
    pipeline, _, ocr, forensics = _pipeline()
    analysis = Analysis(input_type=AnalysisInputType.IMAGE, content="!!!not-base64!!!")

    with pytest.raises(MediaProcessingError, match="not valid base64"):
        pipeline.extract(analysis)

    assert ocr.calls == 0 and forensics.calls == 0


def test_image_input_rejects_empty_payload() -> None:
    """An empty decoded payload is rejected."""
    pipeline, _, _, _ = _pipeline()
    analysis = Analysis(
        input_type=AnalysisInputType.IMAGE,
        content=base64.b64encode(b"").decode(),
    )

    with pytest.raises(MediaProcessingError, match="empty"):
        pipeline.extract(analysis)


def test_url_input_propagates_fetch_error() -> None:
    """An SSRF refusal or network failure surfaces as UrlFetchError."""
    pipeline, _, _, _ = _pipeline(
        fetcher=FakeUrlFetcher(error=UrlFetchError("refused by the SSRF guard"))
    )
    analysis = Analysis(input_type=AnalysisInputType.URL, content="https://example.com/")

    with pytest.raises(UrlFetchError, match="SSRF"):
        pipeline.extract(analysis)


def test_guess_mime_sniffs_common_formats() -> None:
    """The MIME sniffer recognizes PNG, JPEG, GIF, and WebP magic bytes."""
    assert _guess_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert _guess_mime(b"\xff\xd8\xffrest") == "image/jpeg"
    assert _guess_mime(b"GIF89arest") == "image/gif"
    assert _guess_mime(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert _guess_mime(b"unknown") == "application/octet-stream"
