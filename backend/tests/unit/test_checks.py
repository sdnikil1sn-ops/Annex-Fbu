"""Unit tests for readiness dependency checks."""

from __future__ import annotations

from app.core.checks import DatabaseHealthCheck


def test_database_check_reports_unreachable() -> None:
    """An unreachable database is reported as not ok with a detail string."""
    check = DatabaseHealthCheck("postgresql://127.0.0.1:1/annex")
    result = check.check()
    assert result.name == "database"
    assert result.ok is False
    assert result.detail
