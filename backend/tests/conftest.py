"""Shared pytest fixtures for the backend test suite."""

import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture()
def settings() -> Settings:
    """Deterministic test settings (no .env file, quiet logs)."""
    return Settings(_env_file=None, app_env="test", log_level="WARNING")


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """TestClient bound to an application built from test settings.

    ``raise_server_exceptions=False`` lets tests assert on 500 envelopes
    instead of re-raising server errors.
    """
    app = create_app(settings)
    return TestClient(app, raise_server_exceptions=False)
