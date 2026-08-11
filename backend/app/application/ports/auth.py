"""Authentication ports (ADR-0005).

The application layer depends on ``TokenVerifier``; infrastructure provides
implementations (Firebase Admin SDK, and an explicit mock for tests). This
keeps token verification swappable and unit-testable without external
services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class VerifiedIdentity:
    """The identity proven by a verified ID token."""

    uid: UUID
    email: str | None = None
    display_name: str | None = None


class TokenVerificationError(Exception):
    """Raised when an ID token cannot be verified."""


class TokenVerifier(Protocol):
    """Verifies bearer tokens and returns the identity they prove."""

    def verify(self, token: str) -> VerifiedIdentity: ...
