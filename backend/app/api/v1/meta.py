"""Service metadata endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_dep
from app.core.config import Settings

router = APIRouter(tags=["system"])


@router.get("/meta/version")
def version(settings: Settings = Depends(get_settings_dep)) -> dict[str, Any]:
    """Return the API name, version, and runtime environment."""
    return {
        "data": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }
    }
