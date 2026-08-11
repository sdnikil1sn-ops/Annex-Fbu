"""Tests for the Firebase token verifier's configuration boundary."""

from __future__ import annotations

import pytest
from app.infrastructure.auth.firebase_token_verifier import (
    ConfigurationError,
    FirebaseTokenVerifier,
)


def test_missing_service_account_raises_configuration_error() -> None:
    """A nonexistent service-account path must fail fast at construction."""
    with pytest.raises(ConfigurationError):
        FirebaseTokenVerifier("test-project", service_account_path="definitely-missing.json")
