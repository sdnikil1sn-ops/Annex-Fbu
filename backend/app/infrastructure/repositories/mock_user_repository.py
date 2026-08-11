"""In-memory UserRepository for tests (explicit mock per CONTRIBUTING.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.ports.auth import VerifiedIdentity
from app.application.ports.repositories import UserRepository
from app.domain.user import User


class MockUserRepository(UserRepository):
    """A deterministic in-memory user store."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def seed_user(self, user: User) -> None:
        """Pre-populate a user (used to test role enforcement)."""
        self._users[user.id] = user

    def ensure_user(self, identity: VerifiedIdentity) -> None:
        """Create the user row with default profile when absent."""
        if identity.uid not in self._users:
            self._users[identity.uid] = User(
                id=identity.uid,
                email=identity.email,
                display_name=identity.display_name,
                created_at=datetime.now(UTC),
            )

    def get_by_id(self, user_id: UUID) -> User | None:
        """Return the stored user or None."""
        return self._users.get(user_id)
