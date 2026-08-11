"""Shared FastAPI dependencies.

Dependencies are the injection point for the service layer (ADR-0003):
repositories, services, and adapters will be added here in later phases.

Settings are resolved from ``app.state`` — the instance the application was
built with — so tests can inject deterministic settings and every route
shares one configuration object (no global-state surprises).
"""

from typing import cast

from fastapi import Request

from app.core.config import Settings


def get_settings_dep(request: Request) -> Settings:
    """Provide the application-bound settings to request handlers."""
    # app.state is untyped at runtime; the factory guarantees a Settings.
    return cast(Settings, request.app.state.settings)
