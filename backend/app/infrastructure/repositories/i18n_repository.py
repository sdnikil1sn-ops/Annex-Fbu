"""PostgreSQL implementation of the I18nRepository port (ADR-0007).

Locale bundles are read-only, public data: the API reads them through the
service role (which bypasses RLS). Every query is parameterized; the
unique ``(locale_id, namespace, key)`` constraint guarantees at most one
entry per key per locale.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import I18nRepository
from app.domain.i18n import I18nLocale, TranslationEntry


class PostgresI18nRepository(I18nRepository):
    """I18nRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (the Supabase endpoint).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def list_locales(self) -> list[I18nLocale]:
        """Return every enabled locale with its fallback parent."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select code, fallback_code
                from public.i18n_locales
                where enabled
                order by code
                """
            ).fetchall()
        return [I18nLocale(code=row["code"], fallback_code=row["fallback_code"]) for row in rows]

    def translations_for(self, locale_code: str) -> list[TranslationEntry]:
        """Return every translation defined for a locale code."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select t.namespace, t.key, t.value, t.plural_rule, t.version
                from public.i18n_translations t
                join public.i18n_locales l on l.id = t.locale_id
                where l.code = %s
                order by t.namespace, t.key
                """,
                (locale_code,),
            ).fetchall()
        return [
            TranslationEntry(
                namespace=row["namespace"],
                key=row["key"],
                value=row["value"],
                plural_rule=row["plural_rule"],
                version=row["version"],
            )
            for row in rows
        ]
