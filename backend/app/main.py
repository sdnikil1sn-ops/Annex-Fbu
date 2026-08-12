"""Application factory and entry point.

Wires the application core per ADR-0003: configuration, structured
logging, request-ID tracing, the error envelope, CORS, the versioned
router, and the infrastructure ports (database repositories, token
verifier, claim analyzer, media adapters) bound to ``app.state`` for
dependency injection.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.application.ports.ai import ClaimAnalyzer
from app.application.ports.auth import TokenVerifier
from app.application.ports.media import ForensicsAdapter, OcrAdapter
from app.application.services.analysis_service import AnalysisService
from app.application.services.user_service import UserService
from app.core.checks import DatabaseHealthCheck, DependencyCheck
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.infrastructure.ai.factory import build_claim_analyzer
from app.infrastructure.auth.firebase_token_verifier import FirebaseTokenVerifier
from app.infrastructure.media.factory import build_forensics_adapter, build_ocr_adapter
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.repositories.user_repository import PostgresUserRepository


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    user_service: UserService | None = None,
    claim_analyzer: ClaimAnalyzer | None = None,
    ocr_adapter: OcrAdapter | None = None,
    forensics_adapter: ForensicsAdapter | None = None,
    analysis_service: AnalysisService | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional settings override (used by tests); defaults to
            the process-wide cached environment settings.
        token_verifier: Optional verifier override (tests use the mock);
            defaults to a Firebase verifier when Firebase is configured.
        user_service: Optional user service override (tests use mocks);
            defaults to the PostgreSQL-backed service when a database is
            configured.
        claim_analyzer: Optional analyzer override (tests use mocks);
            defaults to the provider selected from settings (ADR-0006).
        ocr_adapter: Optional OCR override; defaults to Tesseract with a
            mock fallback when the binary is missing.
        forensics_adapter: Optional forensics override; defaults to OpenCV.
        analysis_service: Optional analysis service override (tests use the
            in-memory repository); defaults to the PostgreSQL-backed service
            when a database is configured.

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

    # Authentication (ADR-0005): wire the token verifier and the user
    # hydration service from settings unless overridden (tests).
    if token_verifier is None and settings.firebase_project_id:
        token_verifier = FirebaseTokenVerifier(
            settings.firebase_project_id,
            settings.firebase_service_account_path,
        )
    if user_service is None and token_verifier is not None and settings.database_url:
        user_service = UserService(PostgresUserRepository(settings.database_url))
    app.state.token_verifier = token_verifier
    app.state.user_service = user_service

    # AI + media processing (Phase 6, ADR-0006): bind the configured claim
    # analyzer and media adapters to the app so services and endpoints resolve
    # them through DI instead of constructing providers ad hoc. Provider
    # selection is configuration-driven; unconfigured providers fall back to
    # the explicit mocks (local development / tests).
    app.state.claim_analyzer = claim_analyzer or build_claim_analyzer(settings)
    app.state.ocr_adapter = ocr_adapter or build_ocr_adapter(settings)
    app.state.forensics_adapter = forensics_adapter or build_forensics_adapter()

    # Analysis pipeline (Phase 4 domain + Phase 6 API): wire the service
    # from settings unless overridden (tests inject the in-memory mock).
    if analysis_service is None and settings.database_url:
        analysis_service = AnalysisService(PostgresAnalysisRepository(settings.database_url))
    app.state.analysis_service = analysis_service

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
