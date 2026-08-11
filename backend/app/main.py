"""Application factory and entry point.

Wires the application core per ADR-0003: configuration, structured
logging, request-ID tracing, the error envelope, CORS, and the versioned
router. The application/domain/infrastructure layers are added from
Phase 4 onward.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.checks import DatabaseHealthCheck, DependencyCheck
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional settings override (used by tests); defaults to
            the process-wide cached environment settings.

    Returns:
        A fully wired FastAPI application.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level, debug=settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        # The interactive docs UI is a development affordance only.
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
    )
    # Bind the settings instance to the app so routes resolve the same
    # configuration object through DI (see app.api.deps).
    app.state.settings = settings

    # Readiness probes registered from settings (database: Phase 4,
    # Redis: Phase 7). Served by GET /health/ready.
    checks: list[DependencyCheck] = []
    if settings.database_url:
        checks.append(DatabaseHealthCheck(settings.database_url))
    app.state.checks = checks

    # add_middleware prepends: the LAST registration is the OUTERMOST layer.
    # RequestIdMiddleware is registered last so even CORS-preflight responses
    # carry X-REQUEST-ID and the tracing context is active for CORS handling.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    # Unversioned system probes: orchestrators (Cloud Run) must be able to
    # check liveness/readiness without API versioning.
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


def main() -> None:
    """Run the development server (console script ``annex-api``)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )


# Module-level instance for ASGI servers (uvicorn app.main:app). Built once
# at import time; tests construct isolated instances via create_app().
app = create_app()


if __name__ == "__main__":
    main()
