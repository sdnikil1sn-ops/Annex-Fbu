"""Shared FastAPI dependencies.

Settings resolve from ``app.state`` (injected at the factory); the
authenticated caller resolves from the bearer token through the token
verifier + user service also bound to ``app.state`` (ADR-0005).
"""

from collections.abc import Callable
from typing import cast

from fastapi import Request

from app.api.errors import AppError
from app.application.ports.auth import TokenVerificationError, TokenVerifier
from app.application.services.user_service import UserService
from app.core.config import Settings
from app.domain.user import User


def get_settings_dep(request: Request) -> Settings:
    """Provide the application-bound settings to request handlers."""
    # app.state is untyped at runtime; the factory guarantees a Settings.
    return cast(Settings, request.app.state.settings)


def _get_token_verifier(request: Request) -> TokenVerifier:
    """Return the bound token verifier, or 503 when auth is not configured."""
    verifier: TokenVerifier | None = getattr(request.app.state, "token_verifier", None)
    if verifier is None:
        raise AppError(
            "auth.not_configured",
            "Authentication is not configured on this server.",
            status_code=503,
        )
    return verifier


def get_current_user(request: Request) -> User:
    """Resolve the authenticated caller from the bearer token.

    Parses ``Authorization: Bearer <id-token>``, verifies the token through
    the bound verifier (ADR-0005), hydrates the user mirror, and attaches
    the user to ``request.state`` for downstream dependencies.

    Raises:
        AppError 401: missing or invalid token.
        AppError 503: authentication is not configured.
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise AppError("auth.missing_token", "A bearer token is required.", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("auth.missing_token", "A bearer token is required.", status_code=401)

    verifier = _get_token_verifier(request)
    try:
        identity = verifier.verify(token)
    except TokenVerificationError:
        # Never reveal why verification failed (expired vs malformed ...).
        raise AppError(
            "auth.invalid_token", "The token is invalid or expired.", status_code=401
        ) from None

    user_service: UserService = cast(UserService, request.app.state.user_service)
    user = user_service.get_or_create(identity)
    request.state.current_user = user
    return user


def require_roles(*roles: str) -> Callable[[Request], User]:
    """Dependency factory: allow only callers holding one of the given roles.

    Usage: ``def admin_only(user: User = Depends(require_roles("admin"))): ...``

    Authorization is enforced at the service boundary, never only in the
    client UI (SECURITY.md / ADR-0003).

    Args:
        roles: Roles permitted to call the guarded endpoint.

    Returns:
        A FastAPI dependency resolving to the authorized caller.
    """

    def _role_dependency(request: Request) -> User:
        user = get_current_user(request)
        if user.role not in roles:
            raise AppError(
                "auth.insufficient_role",
                "Insufficient role for this operation.",
                status_code=403,
            )
        return user

    return _role_dependency
