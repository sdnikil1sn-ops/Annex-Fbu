"""User service — authentication-time user use cases (ADR-0005)."""

from __future__ import annotations

from uuid import UUID

from app.application.ports.auth import VerifiedIdentity
from app.application.ports.repositories import UserRepository
from app.domain.user import User


class UserNotFoundError(Exception):
    """Raised when a user row cannot be located after hydration."""


class UserService:
    """Hydrates and looks up users behind a repository port.

    Args:
        repository: The user persistence port.
    """

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def get_or_create(self, identity: VerifiedIdentity) -> User:
        """Mirror the identity into the database, then return the user.

        Args:
            identity: The verified identity from the ID token.

        Returns:
            The user with their current role and locale.

        Raises:
            UserNotFoundError: If the row cannot be created or fetched
                (defensive — should not happen on a healthy database).
        """
        self._repository.ensure_user(identity)
        user = self._repository.get_by_id(identity.uid)
        if user is None:
            raise UserNotFoundError(identity.uid)
        return user

    def get(self, user_id: UUID) -> User | None:
        """Fetch a user by ID."""
        return self._repository.get_by_id(user_id)
