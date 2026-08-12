"""Unit tests for readiness dependency checks."""

from __future__ import annotations

import redis
from app.core.checks import DatabaseHealthCheck, RedisHealthCheck


def test_database_check_reports_unreachable() -> None:
    """An unreachable database is reported as not ok with a detail string."""
    check = DatabaseHealthCheck("postgresql://127.0.0.1:1/annex")
    result = check.check()
    assert result.name == "database"
    assert result.ok is False
    assert result.detail


class _PingingClient:
    """A redis client that answers PING."""

    def ping(self) -> bool:
        return True


class _FailingClient:
    """A redis client whose PING raises (as an unreachable server would)."""

    def ping(self) -> bool:
        raise redis.ConnectionError("connection refused")


def test_redis_check_reports_ok() -> None:
    """A reachable Redis is reported ok."""
    check = RedisHealthCheck(_PingingClient())  # type: ignore[arg-type]
    result = check.check()
    assert result.name == "redis"
    assert result.ok is True
    assert result.detail == ""


def test_redis_check_reports_unreachable() -> None:
    """An unreachable Redis is reported not ok with a detail string."""
    check = RedisHealthCheck(_FailingClient())  # type: ignore[arg-type]
    result = check.check()
    assert result.name == "redis"
    assert result.ok is False
    assert result.detail
