"""Application settings loaded from environment variables.

Configuration follows the Twelve-Factor model: every value is overridable
via environment variables (optionally sourced from a local ``.env`` file)
and never hardcoded in application code. The cached instance is provided
through ``get_settings()`` so tests can build their own ``Settings``.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# ``backend/`` — anchored to the module so .env resolution does not depend
# on the process working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Runtime environments the service can run in.
AppEnv = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime configuration for the ANNEX backend.

    Values are read from environment variables (case-insensitive) and from
    a ``backend/.env`` file when present. Unknown environment variables are
    ignored so shared environments do not break the service.
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Product identity.
    app_name: str = "ANNEX API"
    app_version: str = __version__

    # Runtime behavior.
    app_env: AppEnv = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API surface.
    api_v1_prefix: str = "/api/v1"

    # CORS: origins allowed to call the API from browsers.
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached settings (parsed once)."""
    return Settings()
