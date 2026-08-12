"""Tests for the composition-root factories (Phase 6, ADR-0006).

Provider/media selection is exercised without any network access: SDK client
construction is lazy, and the OCR factory's mock fallback is verified against
a fake ``pytesseract`` module so the tests are deterministic whether or not a
Tesseract binary is installed on the machine.
"""

from __future__ import annotations

import sys
import types

import pytest
from app.core.config import Settings
from app.infrastructure.ai.factory import build_claim_analyzer
from app.infrastructure.ai.gemini_claim_analyzer import GeminiClaimAnalyzer
from app.infrastructure.ai.mock_claim_analyzer import MockClaimAnalyzer
from app.infrastructure.ai.openai_claim_analyzer import OpenAIClaimAnalyzer
from app.infrastructure.media.factory import build_forensics_adapter, build_ocr_adapter
from app.infrastructure.media.mock_media_adapters import MockOcrAdapter
from app.infrastructure.media.opencv_forensics import OpenCvForensicsAdapter
from app.infrastructure.media.pytesseract_ocr import TesseractOcrAdapter
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    """Deterministic settings with optional field overrides (no .env file)."""
    return Settings(_env_file=None, app_env="test", log_level="WARNING", **overrides)


def make_fake_pytesseract(*, missing_binary: bool = False) -> types.ModuleType:
    """Build a stand-in ``pytesseract`` module with configurable availability."""

    fake = types.ModuleType("pytesseract")
    fake.TesseractNotFoundError = type("TesseractNotFoundError", (RuntimeError,), {})

    if missing_binary:

        def get_version() -> None:
            raise fake.TesseractNotFoundError("binary missing")

    else:

        def get_version() -> types.SimpleNamespace:
            return types.SimpleNamespace(__str__=lambda self: "5.4.0")

    fake.get_tesseract_version = get_version
    return fake


# ----------------------------------------------------------------------
# Claim-analyzer selection (ADR-0006)
# ----------------------------------------------------------------------


def test_claim_analyzer_defaults_to_mock() -> None:
    """No provider key must yield the explicit mock for local development."""
    assert isinstance(build_claim_analyzer(make_settings()), MockClaimAnalyzer)


def test_claim_analyzer_prefers_openai_when_key_present() -> None:
    """An OpenAI key must select the OpenAI analyzer (primary provider)."""
    analyzer = build_claim_analyzer(make_settings(openai_api_key="sk-test"))
    assert isinstance(analyzer, OpenAIClaimAnalyzer)


def test_claim_analyzer_uses_gemini_when_only_gemini_key() -> None:
    """A Gemini-only configuration must select the Gemini analyzer."""
    analyzer = build_claim_analyzer(
        make_settings(openai_api_key=None, gemini_api_key="gem-test")
    )
    assert isinstance(analyzer, GeminiClaimAnalyzer)


def test_claim_analyzer_uses_configured_openai_model() -> None:
    """The configured model name must reach the OpenAI adapter."""
    analyzer = build_claim_analyzer(
        make_settings(openai_api_key="sk-test", openai_model="gpt-4o")
    )
    assert analyzer._model == "gpt-4o"  # type: ignore[attr-defined]


# ----------------------------------------------------------------------
# Media-adapter selection
# ----------------------------------------------------------------------


def test_ocr_adapter_builds_tesseract_when_binary_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A working Tesseract binary must yield the real OCR adapter."""
    monkeypatch.setitem(sys.modules, "pytesseract", make_fake_pytesseract())
    adapter = build_ocr_adapter(make_settings(ocr_languages="eng+spa"))
    assert isinstance(adapter, TesseractOcrAdapter)
    assert adapter._languages == "eng+spa"  # type: ignore[attr-defined]


def test_ocr_adapter_falls_back_to_mock_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing Tesseract binary must fall back to the explicit mock and log it."""
    monkeypatch.setitem(sys.modules, "pytesseract", make_fake_pytesseract(missing_binary=True))
    assert isinstance(build_ocr_adapter(make_settings()), MockOcrAdapter)
    assert "tesseract binary not found" in caplog.text


def test_forensics_adapter_builds_opencv() -> None:
    """The forensics factory must yield the OpenCV adapter."""
    assert isinstance(build_forensics_adapter(), OpenCvForensicsAdapter)


# ----------------------------------------------------------------------
# Application wiring (composition root)
# ----------------------------------------------------------------------


def test_app_binds_providers_from_settings() -> None:
    """create_app must bind the analyzer and adapters chosen from settings."""
    # Simulate a machine without Tesseract so the OCR binding is deterministic.
    app = create_app(
        Settings(_env_file=None, app_env="test", log_level="WARNING"),
    )
    assert isinstance(app.state.claim_analyzer, MockClaimAnalyzer)
    assert isinstance(app.state.forensics_adapter, OpenCvForensicsAdapter)


def test_app_binds_ocr_fallback_when_tesseract_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An app built without the Tesseract binary must bind the mock OCR."""
    monkeypatch.setitem(sys.modules, "pytesseract", make_fake_pytesseract(missing_binary=True))
    app = create_app(Settings(_env_file=None, app_env="test", log_level="WARNING"))
    assert isinstance(app.state.ocr_adapter, MockOcrAdapter)


def test_app_binds_openai_analyzer_when_key_present() -> None:
    """A configured OpenAI key must reach the bound analyzer."""
    settings = Settings(
        _env_file=None,
        app_env="test",
        log_level="WARNING",
        openai_api_key="sk-test",
    )
    app = create_app(settings)
    assert isinstance(app.state.claim_analyzer, OpenAIClaimAnalyzer)


def test_app_accepts_injected_analyzer() -> None:
    """create_app must honor injected providers over building from settings."""
    injected = MockClaimAnalyzer()
    app = create_app(
        Settings(_env_file=None, app_env="test", log_level="WARNING"),
        claim_analyzer=injected,
    )
    assert app.state.claim_analyzer is injected
