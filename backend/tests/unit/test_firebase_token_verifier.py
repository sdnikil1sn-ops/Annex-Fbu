"""Tests for the Firebase token verifier's configuration boundary."""

from __future__ import annotations

import pytest
from app.core.exceptions import ConfigurationError
from app.infrastructure.auth.firebase_token_verifier import (
    FirebaseTokenVerifier,
    firebase_uid_to_uuid,
)


def test_missing_service_account_raises_configuration_error() -> None:
    """A nonexistent service-account path must fail fast at construction."""
    with pytest.raises(ConfigurationError):
        FirebaseTokenVerifier("test-project", service_account_path="definitely-missing.json")


def test_firebase_uid_to_uuid_passes_through_real_uuids() -> None:
    """UIDs that are already UUIDs must map to themselves."""
    from uuid import UUID

    uid = UUID("3f1f6a9a-4f3a-4a1a-9a0a-9f0a9f0a9f0a")
    assert firebase_uid_to_uuid(str(uid)) == uid


def test_firebase_uid_to_uuid_is_deterministic() -> None:
    """Opaque Firebase UIDs (e.g. `TYBgf1j0ZNho4MygW7dTAwcXpKO2`) must map
    to a stable UUID so real accounts authenticate instead of raising."""
    uid = "TYBgf1j0ZNho4MygW7dTAwcXpKO2"
    first = firebase_uid_to_uuid(uid)
    second = firebase_uid_to_uuid(uid)

    assert str(first) == str(second)
    assert first.version == 5


def test_firebase_uid_to_uuid_distinguishes_different_uids() -> None:
    """Different Firebase UIDs must never collide on the same UUID."""
    a = firebase_uid_to_uuid("user-A")
    b = firebase_uid_to_uuid("user-B")
    assert a != b