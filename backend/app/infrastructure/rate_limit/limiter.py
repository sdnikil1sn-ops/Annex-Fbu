"""Fixed-window rate limiting (Phase 7).

Limits are configured as ``"<count>/<unit>"`` strings (``120/minute``) and
enforced per client key within a fixed window — simple, deterministic, and
adequate for the documented API limits. A no-op limiter keeps the API
bootable and permissive when Redis is not configured, mirroring the mock
fallback pattern of the media adapters.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import ConfigurationError
from app.infrastructure.rate_limit.store import RateLimitStore

# Unit name -> seconds.
_WINDOW_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass(frozen=True)
class RateLimit:
    """One fixed-window limit: ``limit`` requests per ``window_seconds``."""

    limit: int
    window_seconds: int


def parse_rate(value: str) -> RateLimit:
    """Parse a ``"<count>/<unit>"`` rate string into a window limit.

    Raises:
        ConfigurationError: The value is not a valid rate string.
    """
    try:
        count_text, unit = value.strip().lower().split("/")
        count = int(count_text)
        if count < 1:
            raise ValueError("count must be positive")
        window = _WINDOW_SECONDS[unit]
    except (ValueError, KeyError) as exc:
        raise ConfigurationError(
            f"invalid rate limit {value!r} (expected '<count>/<second|minute|hour|day>')"
        ) from exc
    return RateLimit(limit=count, window_seconds=window)


class RateLimiter(Protocol):
    """Decides whether a request for a scope+client key is allowed."""

    def allow(self, scope: str, client_key: str) -> bool:
        """Return True when the request is within the limit (and count it)."""
        ...


class FixedWindowRateLimiter:
    """Counts requests per (scope, client, window) against the configured limit.

    Args:
        store: Counter store (Redis in production, in-memory in tests).
        default_limit: Limit applied to every non-special scope.
        analysis_limit: Limit applied to the analysis endpoints.
        clock: Injectable clock for deterministic tests (defaults to time.time).
    """

    def __init__(
        self,
        store: RateLimitStore,
        default_limit: RateLimit,
        analysis_limit: RateLimit,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._store = store
        self._limits = {"default": default_limit, "analysis": analysis_limit}
        self._clock = clock or time.time

    def allow(self, scope: str, client_key: str) -> bool:
        limit = self._limits.get(scope, self._limits["default"])
        window_start = int(self._clock() // limit.window_seconds)
        key = f"rl:{scope}:{client_key}:{window_start}"
        count = self._store.increment_and_get(key, limit.window_seconds)
        return count <= limit.limit


class NoopRateLimiter:
    """Allows every request (used when Redis is not configured)."""

    def allow(self, scope: str, client_key: str) -> bool:
        return True
