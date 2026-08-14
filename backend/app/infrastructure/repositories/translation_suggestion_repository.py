"""PostgreSQL implementation of the TranslationSuggestionRepository port (Phase 18).

``translation_suggestions`` is a review queue for community translations
(migration 20260814000001): contributors submit proposed values for
keys, moderators approve/reject, and the service publishes approved
values into ``i18n_translations`` via the I18nRepository. The partial
unique index keeps one pending suggestion per (user, locale, key) so
re-submission is an update, not a duplicate. Every query is
parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import TranslationSuggestionRepository
from app.domain.i18n import MissingKey, TranslationSuggestion


class PostgresTranslationSuggestionRepository(TranslationSuggestionRepository):
    """TranslationSuggestionRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def list_missing(
        self, locale_code: str, default_locale: str = "en"
    ) -> list[MissingKey]:
        """Return keys the default locale defines that ``locale_code`` lacks.

        The default locale's entry set is the source of truth for what
        should exist everywhere (ADR-0007): a key is 'missing' for a
        locale when no translation row exists there. Approved suggestions
        are already published into ``i18n_translations``, so they stop
        being missing naturally.
        """
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select base.namespace, base.key, base.value as english_value
                from public.i18n_translations base
                join public.i18n_locales bl on bl.id = base.locale_id
                where bl.code = %s
                  and not exists (
                      select 1
                      from public.i18n_translations loc
                      join public.i18n_locales ll on ll.id = loc.locale_id
                      where ll.code = %s
                        and loc.namespace = base.namespace
                        and loc.key = base.key
                  )
                order by base.namespace, base.key
                """,
                (default_locale, locale_code),
            ).fetchall()
        return [
            MissingKey(
                namespace=row["namespace"],
                key=row["key"],
                english_value=row["english_value"],
            )
            for row in rows
        ]

    def submit(self, suggestion: TranslationSuggestion) -> TranslationSuggestion | None:
        """Insert a suggestion, updating the contributor's own pending row.

        Returns None when the target locale is unknown or disabled. The
        partial unique index (pending per user + locale + key) turns a
        re-submission into an update of the existing pending row.
        """
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                insert into public.translation_suggestions
                    (locale_id, namespace, key, value, plural_rule, suggested_by)
                select l.id, %s, %s, %s, %s, %s
                from public.i18n_locales l
                where l.code = %s and l.enabled
                on conflict (locale_id, namespace, key, suggested_by)
                    where status = 'pending'
                do update set
                    value = excluded.value,
                    plural_rule = excluded.plural_rule
                returning id, namespace, key, value, plural_rule,
                          suggested_by, status, created_at, reviewed_by, reviewed_at
                """,
                (
                    suggestion.namespace,
                    suggestion.key,
                    suggestion.value,
                    suggestion.plural_rule,
                    suggestion.suggested_by,
                    suggestion.locale_code,
                ),
            ).fetchone()
        if row is None:
            return None
        return _suggestion_from_row(row, suggestion.locale_code)

    def get(self, suggestion_id: UUID) -> TranslationSuggestion | None:
        """Fetch one suggestion with its locale code attached."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select s.id, l.code as locale_code, s.namespace, s.key, s.value,
                       s.plural_rule, s.suggested_by, s.status, s.created_at,
                       s.reviewed_by, s.reviewed_at
                from public.translation_suggestions s
                join public.i18n_locales l on l.id = s.locale_id
                where s.id = %s
                """,
                (suggestion_id,),
            ).fetchone()
        return _suggestion_from_row(row) if row else None

    def list_for_user(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[TranslationSuggestion]:
        """Return a contributor's suggestions, newest first."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select s.id, l.code as locale_code, s.namespace, s.key, s.value,
                       s.plural_rule, s.suggested_by, s.status, s.created_at,
                       s.reviewed_by, s.reviewed_at
                from public.translation_suggestions s
                join public.i18n_locales l on l.id = s.locale_id
                where s.suggested_by = %s
                  and (%s::text is null or s.status = %s)
                order by s.created_at desc, s.id
                """,
                (user_id, status, status),
            ).fetchall()
        return [_suggestion_from_row(row) for row in rows]

    def list_pending(self, *, limit: int = 50) -> list[TranslationSuggestion]:
        """Return the moderator review queue, oldest first."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select s.id, l.code as locale_code, s.namespace, s.key, s.value,
                       s.plural_rule, s.suggested_by, s.status, s.created_at,
                       s.reviewed_by, s.reviewed_at
                from public.translation_suggestions s
                join public.i18n_locales l on l.id = s.locale_id
                where s.status = 'pending'
                order by s.created_at, s.id
                limit %s
                """,
                (limit,),
            ).fetchall()
        return [_suggestion_from_row(row) for row in rows]

    def review(
        self, suggestion_id: UUID, reviewer_id: UUID, approved: bool
    ) -> TranslationSuggestion | None:
        """Mark a suggestion approved or rejected (pending rows only).

        Returns None when the suggestion does not exist or was already
        reviewed — a suggestion can change status only once.
        """
        status = "approved" if approved else "rejected"
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                update public.translation_suggestions
                set status = %s, reviewed_by = %s, reviewed_at = now()
                where id = %s and status = 'pending'
                returning id, namespace, key, value, plural_rule,
                          suggested_by, status, created_at, reviewed_by, reviewed_at
                """,
                (status, reviewer_id, suggestion_id),
            ).fetchone()
            if row is None:
                return None
            locale_row: dict[str, Any] | None = conn.execute(
                "select code from public.i18n_locales where id = ("
                "  select locale_id from public.translation_suggestions where id = %s"
                ")",
                (suggestion_id,),
            ).fetchone()
        assert locale_row is not None
        return _suggestion_from_row(row, locale_row["code"])


def _suggestion_from_row(
    row: dict[str, Any], locale_code: str | None = None
) -> TranslationSuggestion:
    """Map a suggestion row to the domain aggregate."""
    return TranslationSuggestion(
        id=row["id"],
        locale_code=locale_code or row.get("locale_code", ""),
        namespace=row["namespace"],
        key=row["key"],
        value=row["value"],
        plural_rule=row["plural_rule"],
        suggested_by=row["suggested_by"],
        status=row["status"],
        created_at=row["created_at"],
        reviewed_by=row["reviewed_by"],
        reviewed_at=row["reviewed_at"],
    )
