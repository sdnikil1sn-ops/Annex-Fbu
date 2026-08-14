"""Unit tests for the TranslationSuggestionService (Phase 18)."""

from __future__ import annotations

from uuid import uuid4

from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.domain.i18n import SUGGESTION_APPROVED, SUGGESTION_PENDING, SUGGESTION_REJECTED
from app.infrastructure.repositories.mock_i18n_repository import MockI18nRepository
from app.infrastructure.repositories.mock_translation_suggestion_repository import (
    MockTranslationSuggestionRepository,
)


def _service() -> tuple[
    TranslationSuggestionService,
    MockTranslationSuggestionRepository,
    MockI18nRepository,
]:
    repository = MockTranslationSuggestionRepository()
    i18n = MockI18nRepository.seeded()
    service = TranslationSuggestionService(repository, i18n)
    return service, repository, i18n


def test_missing_lists_untranslated_keys() -> None:
    """Keys defined in en but missing for pt are listed with the source text."""
    service, repository, _ = _service()
    repository.seed_translation("en", "common", "cancel", "Cancel")
    repository.seed_translation("en", "common", "save", "Save")
    repository.seed_translation("pt", "common", "cancel", "Cancelar")

    missing = service.missing("pt")
    assert [(item.full_key, item.english_value) for item in missing] == [
        ("common.save", "Save")
    ]


def test_missing_unknown_locale_is_empty() -> None:
    """A locale outside the enabled set resolves to no missing keys."""
    service, _, _ = _service()
    assert service.missing("zz") == []


def test_submit_creates_pending_suggestion() -> None:
    """Submitting a proposal returns a pending suggestion for the locale."""
    service, _, _ = _service()
    contributor = uuid4()

    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")

    assert suggestion is not None
    assert suggestion.locale_code == "pt"
    assert suggestion.status == SUGGESTION_PENDING
    assert suggestion.suggested_by == contributor
    assert suggestion.value == "Salvar"


def test_submit_updates_own_pending_suggestion() -> None:
    """Re-submitting the same key updates the same pending suggestion."""
    service, _, _ = _service()
    contributor = uuid4()

    first = service.submit(contributor, "pt", "common", "save", "Salvar")
    second = service.submit(contributor, "pt", "common", "save", "Gravar")

    assert first is not None and second is not None
    assert first.id == second.id
    assert second.value == "Gravar"
    assert len(service.list_for_user(contributor)) == 1


def test_submit_rejects_unknown_locale() -> None:
    """An unknown locale yields None, not an error."""
    service, _, _ = _service()

    assert service.submit(uuid4(), "zz", "common", "save", "Sichern") is None


def test_list_for_user_filters_by_status() -> None:
    """Status filtering returns only the requested state."""
    service, repository, _ = _service()
    contributor = uuid4()
    pending = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert pending is not None
    approved = repository.seed_suggestion(
        "pt", "common", "cancel", "Cancelar", contributor, status=SUGGESTION_APPROVED
    )

    all_items = service.list_for_user(contributor)
    assert {item.id for item in all_items} == {pending.id, approved.id}

    pending_items = service.list_for_user(contributor, status=SUGGESTION_PENDING)
    assert [item.id for item in pending_items] == [pending.id]


def test_review_approves_and_publishes() -> None:
    """Approving publishes the value into i18n_translations with a bump."""
    service, repository, i18n = _service()
    contributor, moderator = uuid4(), uuid4()
    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert suggestion is not None

    reviewed = service.review(suggestion.id, moderator, approved=True)

    assert reviewed is not None
    assert reviewed.status == SUGGESTION_APPROVED
    assert reviewed.reviewed_by == moderator
    assert reviewed.reviewed_at is not None

    # The value is now live in the service's i18n store with a version bump.
    published = next(
        entry
        for entry in i18n.translations_for("pt")
        if entry.namespace == "common" and entry.key == "save"
    )
    assert published.value == "Salvar"
    assert published.version == 2


def test_review_rejects_without_publishing() -> None:
    """Rejecting marks the suggestion rejected and publishes nothing."""
    service, _, _ = _service()
    contributor, moderator = uuid4(), uuid4()
    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert suggestion is not None

    reviewed = service.review(suggestion.id, moderator, approved=False)

    assert reviewed is not None
    assert reviewed.status == SUGGESTION_REJECTED
    assert reviewed.reviewed_at is not None


def test_review_only_once() -> None:
    """A reviewed suggestion cannot be reviewed again."""
    service, _, _ = _service()
    contributor, moderator = uuid4(), uuid4()
    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert suggestion is not None

    first = service.review(suggestion.id, moderator, approved=True)
    second = service.review(suggestion.id, moderator, approved=False)

    assert first is not None and first.status == SUGGESTION_APPROVED
    assert second is None


def test_review_unknown_suggestion_is_none() -> None:
    """An unknown suggestion id yields None, not an error."""
    service, _, _ = _service()
    assert service.review(uuid4(), uuid4(), approved=True) is None


def test_list_pending_oldest_first() -> None:
    """The review queue is oldest-first."""
    service, _, _ = _service()
    contributor = uuid4()
    first = service.submit(contributor, "pt", "common", "save", "Salvar")
    second = service.submit(contributor, "pt", "common", "cancel", "Cancelar")
    assert first is not None and second is not None

    queue = service.list_pending()
    assert [item.id for item in queue] == [first.id, second.id]
