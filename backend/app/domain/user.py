"""User aggregate — mirrored from the Firebase identity (ADR-0005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class User:
    """A verified ANNEX user.

    Attributes:
        id: Firebase UID (primary key of the ``users`` table).
        email: Verified email, when provided.
        display_name: Display name, when provided.
        role: Authorization role (``user`` | ``moderator`` | ``admin``).
        locale: Current UI language.
        created_at: When the user was first seen.
    """

    id: UUID
    email: str | None = None
    display_name: str | None = None
    role: str = "user"
    locale: str = "en"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
