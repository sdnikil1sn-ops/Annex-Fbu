"""Explicit mock TokenVerifier for tests and local development.

Accepts only the tokens present in the configured identity map; anything
else is rejected exactly like an unverifiable real token.
"""

from __future__ import annotations

from app.application.ports.auth import TokenVerificationError, TokenVerifier, VerifiedIdentity


class MockTokenVerifier(TokenVerifier):
    """A deterministic token verifier keyed on known tokens.

    Args:
        identities: Mapping of token string -> verified identity.
    """

    def __init__(self, identities: dict[str, VerifiedIdentity] | None = None) -> None:
        self._identities = identities or {}

    def verify(self, token: str) -> VerifiedIdentity:
        """Return the identity for a known token, else reject."""
        identity = self._identities.get(token)
        if identity is None:
            raise TokenVerificationError("unknown token")
        return identity
