"""Unit tests: I18nService bundle resolution (ADR-0007).

Covers the fallback chain contract — missing key → parent → en, the
requested locale winning over fallbacks, bundle versioning, and the
unknown/disabled locale path.
"""

from __future__ import annotations

import pytest
from app.application.services.i18n_service import I18nService
from app.domain.i18n import ResolvedBundle
from app.infrastructure.repositories.mock_i18n_repository import MockI18nRepository


@pytest.fixture()
def service() -> I18nService:
    """A service over the seeded mock (en, pt->en, es->en)."""
    return I18nService(MockI18nRepository.seeded(), default_locale="en")


def test_default_locale_is_exposed(service: I18nService) -> None:
    """The chain root is part of the service contract."""
    assert service.default_locale == "en"


def test_list_locales_returns_enabled_with_fallbacks(service: I18nService) -> None:
    """The locale list carries each enabled locale's fallback parent."""
    locales = {loc.code: loc.fallback_code for loc in service.list_locales()}
    assert locales == {"en": None, "pt": "en", "es": "en"}


def test_default_locale_bundle_has_no_fallback(service: I18nService) -> None:
    """The default locale resolves alone and keeps its own entries."""
    bundle = service.bundle("en")
    assert bundle is not None
    assert bundle.locale == "en"
    assert bundle.fallback_locale is None
    assert bundle.entries["common.cancel"].value == "Cancel"
    assert bundle.entries["errors.generic"].value == "Something went wrong. Please try again."


def test_pt_bundle_overrides_and_falls_back_to_en(service: I18nService) -> None:
    """pt wins on its own keys and inherits missing keys from en."""
    bundle = service.bundle("pt")
    assert bundle is not None
    assert bundle.locale == "pt"
    assert bundle.fallback_locale == "en"
    assert bundle.entries["common.cancel"].value == "Cancelar"  # pt wins
    assert bundle.entries["analysis.submit"].value == "Analisar"  # pt wins
    assert bundle.entries["errors.generic"].value == "Something went wrong. Please try again."


def test_es_bundle_falls_back_to_en(service: I18nService) -> None:
    """es defines only a couple of keys; the rest resolve through en."""
    bundle = service.bundle("es")
    assert bundle is not None
    assert bundle.entries["common.cancel"].value == "Cancelar"  # es wins
    assert bundle.entries["common.save"].value == "Save"  # from en


def test_locale_lookup_is_case_insensitive(service: I18nService) -> None:
    """``PT`` and ``pt`` resolve to the same bundle."""
    assert service.bundle("PT") == service.bundle("pt")


def test_unknown_locale_returns_none(service: I18nService) -> None:
    """A locale that is not enabled yields no bundle (the API 404s)."""
    assert service.bundle("zz") is None


def test_version_is_max_entry_version() -> None:
    """The bundle version tracks the newest entry revision."""
    repository = MockI18nRepository.seeded()
    repository.add_translation("pt", "common", "new_key", "Novo", version=4)
    service = I18nService(repository, default_locale="en")

    bundle = service.bundle("pt")
    assert bundle is not None
    assert bundle.version == 4


def test_multi_level_fallback_chain() -> None:
    """A three-level chain (fr -> pt -> en) fills keys at each hop."""
    repository = MockI18nRepository.seeded()
    repository.add_locale("fr", fallback_code="pt")
    repository.add_translation("fr", "common", "retry", "Réessayer")
    service = I18nService(repository, default_locale="en")

    bundle = service.bundle("fr")
    assert bundle is not None
    assert bundle.fallback_locale == "pt"
    assert bundle.entries["common.retry"].value == "Réessayer"  # fr wins
    assert bundle.entries["common.cancel"].value == "Cancelar"  # from pt
    assert bundle.entries["errors.generic"].value == "Something went wrong. Please try again."


def test_fallback_to_absent_locale_terminates_chain() -> None:
    """A fallback code with no matching locale must not raise (regression)."""
    repository = MockI18nRepository.seeded()
    repository.add_locale("xx", fallback_code="does-not-exist")
    repository.add_translation("xx", "common", "cancel", "X")
    service = I18nService(repository, default_locale="en")

    bundle = service.bundle("xx")
    assert bundle is not None
    assert bundle.entries["common.cancel"].value == "X"
    # The absent parent is skipped; en still terminates the chain.
    assert bundle.entries["common.save"].value == "Save"


def test_resolved_bundle_is_frozen_shape(service: I18nService) -> None:
    """The resolved bundle exposes the documented fields."""
    bundle = service.bundle("pt")
    assert isinstance(bundle, ResolvedBundle)
    assert bundle.entries["common.cancel"].plural_rule == "none"
    assert bundle.entries["common.cancel"].full_key == "common.cancel"
