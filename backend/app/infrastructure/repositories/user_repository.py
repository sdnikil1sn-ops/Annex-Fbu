"""PostgreSQL implementation of the UserRepository port.

Mirrors Firebase identities into ``users`` + ``profiles`` (ADR-0005) using
parameterized, idempotent upserts.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.application.ports.auth import VerifiedIdentity
from app.application.ports.repositories import UserRepository
from app.domain.user import User


class PostgresUserRepository(UserRepository):
    """UserRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def ensure_user(self, identity: VerifiedIdentity) -> None:
        """Insert the user + default profile when they do not exist."""
        with self._connect() as conn:
            conn.execute(
                """
                insert into public.users (id, email, display_name)
                values (%s, %s, %s)
                on conflict (id) do nothing
                """,
                (identity.uid, identity.email, identity.display_name),
            )
            conn.execute(
                """
                insert into public.profiles (user_id, locale)
                values (%s, %s)
                on conflict (user_id) do nothing
                """,
                (identity.uid, "en"),
            )

    def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user with their current role and locale."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select u.id, u.email, u.display_name, p.role, p.locale, u.created_at
                from public.users u
                left join public.profiles p on p.user_id = u.id
                where u.id = %s
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            display_name=row["display_name"],
            role=row["role"],
            locale=row["locale"],
            created_at=row["created_at"],
        )
