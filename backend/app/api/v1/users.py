"""User endpoints — all routes require a verified Firebase ID token."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.domain.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Return the authenticated caller's profile.

    Requires ``Authorization: Bearer <Firebase ID token>``. The user is
    hydrated into the database on first access (ADR-0005).
    """
    return {
        "data": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "locale": user.locale,
        }
    }
