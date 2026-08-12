"""Integration tests: PostgresI18nRepository against a real database.

Gated on TEST_DATABASE_URL; the schema (including the i18n seed
migration) is applied from the versioned migrations on every run.
"""

from __future__ import annotations

import os

import pytest
from app.application.ports.repositories import I18nRepository
from app.application.services.i18n_service import I18nService
from app.infrastructure.repositories.i18n_repository import PostgresI18nRepository

from tests.integration.helpers import apply_migrations

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> I18nRepository:
    """A fresh-schema Postgres i18n repository per test."""
    apply_migrations(TEST_DSN)
    return PostgresI18nRepository(TEST_DSN)


def test_list_locales_returns_seed_locales(repository: I18nRepository) -> None:
    """The seed migration provides the enabled locales with fallbacks."""
    locales = {locale.code: locale.fallback_code for locale in repository.list_locales()}
    assert locales["en"] is None
    assert locales["pt"] == "en"
    assert locales["ar"] == "en"
    assert "ja" in locales


def test_translations_for_english(repository: I18nRepository) -> None:
    """The English seed carries the full base key set."""
    entries = {entry.full_key: entry for entry in repository.translations_for("en")}
    assert entries["common.cancel"].value == "Cancel"
    assert entries["common.claims_count"].plural_rule == "other"
    assert "analysis.summary" in entries


def test_translations_for_portuguese_are_subset(repository: I18nRepository) -> None:
    """Non-default locales define a subset — missing keys come from en."""
    pt_entries = {entry.full_key for entry in repository.translations_for("pt")}
    en_entries = {entry.full_key for entry in repository.translations_for("en")}
    assert "common.cancel" in pt_entries
    assert pt_entries < en_entries


def test_service_resolves_pt_bundle_over_postgres(repository: I18nRepository) -> None:
    """The full resolution path works against real PostgreSQL."""
    service = I18nService(repository, default_locale="en")

    bundle = service.bundle("pt")
    assert bundle is not None
    assert bundle.fallback_locale == "en"
    assert bundle.entries["common.cancel"].value == "Cancelar"  # pt wins
    assert bundle.entries["errors.generic"].value == "Something went wrong. Please try again."

    assert service.bundle("zz") is None
