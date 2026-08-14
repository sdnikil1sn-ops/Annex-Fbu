"""Integration tests: PostgresTranslationSuggestionRepository + publish.

Gated on TEST_DATABASE_URL; the schema (including the Phase 18
suggestion migration and the i18n seed) is applied from the versioned
migrations on every run. The full review path is exercised end-to-end:
submit -> approve -> the value lands in i18n_translations with a bumped
version, so the live bundle changes without a release.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.application.ports.repositories import (
    I18nRepository,
    TranslationSuggestionRepository,
)
from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.infrastructure.repositories.i18n_repository import PostgresI18nRepository
from app.infrastructure.repositories.translation_suggestion_repository import (
    PostgresTranslationSuggestionRepository,
)

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> TranslationSuggestionRepository:
    """A fresh-schema Postgres suggestion repository per test (seeded)."""
    apply_migrations(TEST_DSN)
    return PostgresTranslationSuggestionRepository(TEST_DSN)


@pytest.fixture()
def i18n_repository() -> I18nRepository:
    """The live translation store used by the review publish path."""
    return PostgresI18nRepository(TEST_DSN)


def test_list_missing_reports_seed_gaps(
    repository: TranslationSuggestionRepository,
) -> None:
    """Keys the seed defines in en but not in pt show up as missing."""
    missing = repository.list_missing("pt")
    keys = {item.full_key for item in missing}
    assert "common.save" in keys
    assert "errors.generic" in keys
    # pt defines cancel, so it is not missing.
    assert "common.cancel" not in keys


def test_submit_creates_and_updates_pending(
    repository: TranslationSuggestionRepository,
) -> None:
    """Submitting creates a pending row; re-submission updates it."""
    contributor = uuid4()
    create_user(TEST_DSN, contributor)
    from app.domain.i18n import TranslationSuggestion

    first = repository.submit(
        TranslationSuggestion(
            locale_code="pt",
            namespace="common",
            key="save",
            value="Salvar",
            suggested_by=contributor,
        )
    )
    assert first is not None and first.status == "pending"

    second = repository.submit(
        TranslationSuggestion(
            locale_code="pt",
            namespace="common",
            key="save",
            value="Gravar",
            suggested_by=contributor,
        )
    )
    assert second is not None and second.id == first.id and second.value == "Gravar"
    assert len(repository.list_for_user(contributor)) == 1


def test_submit_unknown_locale_is_none(repository: TranslationSuggestionRepository) -> None:
    """An unknown locale yields None (no row is created)."""
    from app.domain.i18n import TranslationSuggestion

    assert (
        repository.submit(
            TranslationSuggestion(
                locale_code="zz",
                namespace="common",
                key="save",
                value="X",
                suggested_by=uuid4(),
            )
        )
        is None
    )


def test_review_approve_publishes_with_version_bump(
    repository: TranslationSuggestionRepository,
    i18n_repository: I18nRepository,
) -> None:
    """Approving publishes into i18n_translations; bundles pick it up."""
    contributor, moderator = uuid4(), uuid4()
    create_user(TEST_DSN, contributor)
    create_user(TEST_DSN, moderator)
    service = TranslationSuggestionService(repository, i18n_repository)

    before = i18n_repository.translations_for("pt")
    before_version = {
        entry.full_key: entry.version
        for entry in before
        if entry.namespace == "common" and entry.key == "save"
    }.get("common.save", 0)

    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert suggestion is not None

    reviewed = service.review(suggestion.id, moderator, approved=True)
    assert reviewed is not None and reviewed.status == "approved"
    assert reviewed.reviewed_by == moderator
    assert reviewed.reviewed_at is not None

    published = next(
        entry
        for entry in i18n_repository.translations_for("pt")
        if entry.namespace == "common" and entry.key == "save"
    )
    assert published.value == "Salvar"
    assert published.version == before_version + 1

    # The suggestion can no longer be reviewed.
    assert service.review(suggestion.id, moderator, approved=False) is None


def test_review_reject_publishes_nothing(
    repository: TranslationSuggestionRepository,
    i18n_repository: I18nRepository,
) -> None:
    """Rejecting marks the row rejected and changes no translations."""
    contributor, moderator = uuid4(), uuid4()
    create_user(TEST_DSN, contributor)
    create_user(TEST_DSN, moderator)
    service = TranslationSuggestionService(repository, i18n_repository)

    suggestion = service.submit(contributor, "pt", "common", "save", "Salvar")
    assert suggestion is not None

    reviewed = service.review(suggestion.id, moderator, approved=False)
    assert reviewed is not None and reviewed.status == "rejected"

    entries = {
        entry.full_key: entry.value for entry in i18n_repository.translations_for("pt")
    }
    assert "common.save" not in entries


def test_pending_queue_and_get(repository: TranslationSuggestionRepository) -> None:
    """Pending suggestions appear in the queue; get fetches by id."""
    contributor = uuid4()
    create_user(TEST_DSN, contributor)
    from app.domain.i18n import TranslationSuggestion

    suggestion = repository.submit(
        TranslationSuggestion(
            locale_code="pt",
            namespace="common",
            key="save",
            value="Salvar",
            suggested_by=contributor,
        )
    )
    assert suggestion is not None

    queue = repository.list_pending()
    assert [item.id for item in queue] == [suggestion.id]

    fetched = repository.get(suggestion.id)
    assert fetched is not None and fetched.locale_code == "pt"
    assert repository.get(uuid4()) is None
