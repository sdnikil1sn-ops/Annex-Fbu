"""Helpers for PostgreSQL-backed integration tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import psycopg

# Project root (backend/tests/integration -> project root).
REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def apply_migrations(dsn: str) -> None:
    """Reset the schema and apply every versioned migration in order.

    A minimal ``auth.uid()`` stub is installed first so RLS policies that
    reference the Supabase auth schema parse on a plain PostgreSQL server.
    """
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("drop schema if exists public cascade")
        conn.execute("create schema public")
        conn.execute("create schema if not exists auth")
        conn.execute(
            "create or replace function auth.uid() returns uuid "
            "language sql stable as $$ select null::uuid $$"
        )
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            # Strip comment lines before splitting so semicolons inside
            # prose comments never fragment statements.
            body = "\n".join(
                line
                for line in migration.read_text(encoding="utf-8").splitlines()
                if not line.lstrip().startswith("--")
            )
            statements = [statement.strip() for statement in body.split(";") if statement.strip()]
            for statement in statements:
                conn.execute(statement)


def create_user(dsn: str, user_id: UUID) -> None:
    """Seed a users row so analyses can reference it as an owner."""
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "insert into public.users (id, email) values (%s, %s)",
            (user_id, f"{user_id}@example.invalid"),
        )
