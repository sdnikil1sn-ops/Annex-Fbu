"""Explicit mocks for the media ports (tests and local development)."""

from __future__ import annotations

from app.application.ports.media import (
    ForensicsAdapter,
    ForensicsReport,
    OcrAdapter,
    OcrResult,
)


class MockOcrAdapter(OcrAdapter):
    """Returns a fixed OCR result and counts calls."""

    def __init__(self, result: OcrResult | None = None) -> None:
        self._result = result or OcrResult(text="mock ocr text", confidence=0.9, language="eng")
        self.calls = 0

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        self.calls += 1
        return self._result


class MockForensicsAdapter(ForensicsAdapter):
    """Returns a fixed forensics report and counts calls."""

    def __init__(self, report: ForensicsReport | None = None) -> None:
        self._report = report or ForensicsReport(signals={"mock": True}, risk_score=0.0)
        self.calls = 0

    def analyze(self, image_bytes: bytes) -> ForensicsReport:
        self.calls += 1
        return self._report
