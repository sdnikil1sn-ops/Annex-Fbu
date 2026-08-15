"""Unit tests for the configuration layer."""

import pytest
from app import __version__
from app.core.config import Settings


def test_defaults() -> None:
    """Defaults must reflect the project identity and safe development values."""
    settings = Settings(_env_file=None)
    assert settings.app_name == "ANNEX API"
    assert settings.app_version == __version__
    assert settings.app_env == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.api_v1_prefix == "/api/v1"
    assert "http://localhost:3000" in settings.allowed_origins


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables must override defaults (Twelve-Factor)."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_NAME", "ANNEX API (test)")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.app_name == "ANNEX API (test)"


def test_database_url_defaults_to_none() -> None:
    """The database is opt-in: no URL means no DB wiring."""
    settings = Settings(_env_file=None)
    assert settings.database_url is None


def test_ai_provider_defaults() -> None:
    """AI provider keys must be opt-in; models default to the pinned names."""
    settings = Settings(_env_file=None)
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.gemini_api_key is None
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    assert settings.ocr_languages == "eng"


def test_ai_provider_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI keys and model names must be configurable via the environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test")
    monkeypatch.setenv("OCR_LANGUAGES", "eng+spa")
    settings = Settings(_env_file=None)
    assert settings.openai_api_key == "sk-test"
    assert settings.openai_model == "gpt-4o"
    assert settings.gemini_api_key == "gem-test"
    assert settings.ocr_languages == "eng+spa"


def test_phase7_pipeline_defaults() -> None:
    """Redis/Celery are opt-in; rate limits default to the documented values."""
    settings = Settings(_env_file=None)
    assert settings.redis_url is None
    assert settings.celery_broker_url is None
    assert settings.celery_result_backend is None
    assert settings.rate_limit_default == "120/minute"
    assert settings.rate_limit_analysis == "20/minute"


def test_phase7_pipeline_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis/Celery endpoints and rate limits must be env-configurable."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "10/second")
    monkeypatch.setenv("RATE_LIMIT_ANALYSIS", "5/minute")
    settings = Settings(_env_file=None)
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.celery_broker_url == "redis://localhost:6379/1"
    assert settings.celery_result_backend == "redis://localhost:6379/2"
    assert settings.rate_limit_default == "10/second"
    assert settings.rate_limit_analysis == "5/minute"


def test_unknown_env_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown variables must not crash settings parsing."""
    monkeypatch.setenv("TOTALLY_UNKNOWN_ANNEX_VAR", "whatever")
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
