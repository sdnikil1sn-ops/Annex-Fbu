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


def test_unknown_env_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown variables must not crash settings parsing."""
    monkeypatch.setenv("TOTALLY_UNKNOWN_ANNEX_VAR", "whatever")
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
