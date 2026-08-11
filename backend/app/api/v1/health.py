"""Service health endpoints.

``/health`` is an unauthenticated liveness probe; ``/health/ready`` reports
readiness of configured dependencies (database: Phase 4, Redis: Phase 7).
Both live outside the versioned prefix so orchestrators can probe them
without API versioning.
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_dep
from app.core.config import Settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings_dep)) -> dict[str, Any]:
    """Liveness probe — 200 whenever the process is serving requests."""
    return {
        "data": {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }
    }


@router.get("/health/ready")
def readiness() -> dict[str, Any]:
    """Readiness probe — reports the status of configured dependencies.

    Dependency checks are registered in later phases (database in Phase 4,
    Redis in Phase 7). An empty check list means the service is ready by
    definition today.
    """
    checks: list[dict[str, Any]] = []
    return {"data": {"status": "ok", "checks": checks}}
