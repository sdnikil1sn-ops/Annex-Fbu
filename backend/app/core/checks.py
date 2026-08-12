"""Readiness dependency checks for the /health/ready endpoint.

Each dependency registers a probe; the endpoint reports degraded (503) as
soon as one probe fails, with per-check detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg
import redis


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one readiness probe."""

    name: str
    ok: bool
    detail: str = ""


class DependencyCheck(Protocol):
    """A probe reporting whether a dependency is ready."""

    name: str

    def check(self) -> CheckResult: ...


class DatabaseHealthCheck:
    """Probes PostgreSQL with a lightweight ``select 1``.

    Args:
        dsn: PostgreSQL connection string.
    """

    name = "database"

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def check(self) -> CheckResult:
        """Return ok only when the database answers a trivial query."""
        try:
            with psycopg.connect(self._dsn, connect_timeout=2) as conn:
                conn.execute("select 1")
            return CheckResult(name=self.name, ok=True)
        except psycopg.Error as exc:
            return CheckResult(name=self.name, ok=False, detail=str(exc))


class RedisHealthCheck:
    """Probes Redis with a lightweight PING.

    Args:
        client: The shared application Redis client (bound in the factory).
    """

    name = "redis"

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def check(self) -> CheckResult:
        """Return ok only when Redis answers PING."""
        try:
            self._client.ping()
            return CheckResult(name=self.name, ok=True)
        except redis.RedisError as exc:
            return CheckResult(name=self.name, ok=False, detail=str(exc))
