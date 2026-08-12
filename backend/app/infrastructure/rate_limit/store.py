"""Counter stores for fixed-window rate limiting (Phase 7).

The limiter computes the window key; a store only has to increment a key
with a TTL hint. Redis is the production store; the in-memory store backs
tests and single-process development without a broker.
"""

from __future__ import annotations

from typing import Protocol

import redis


class RateLimitStore(Protocol):
    """Atomic increment-with-TTL primitive behind the limiter."""

    def increment_and_get(self, key: str, ttl_seconds: int) -> int:
        """Increment ``key`` and return its new value."""
        ...


class RedisRateLimitStore:
    """Redis-backed counter using an INCR + EXPIRE-NX pipeline.

    ``EXPIRE ... NX`` sets the TTL only on the first increment of a window,
    so a hot key's TTL is never pushed out by later requests.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def increment_and_get(self, key: str, ttl_seconds: int) -> int:
        pipeline = self._client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, ttl_seconds, nx=True)
        results = pipeline.execute()
        return int(results[0])


class InMemoryRateLimitStore:
    """Thread-unsafe in-memory counters for tests and local development."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def increment_and_get(self, key: str, ttl_seconds: int) -> int:
        # Fixed-window keys already encode the window start, so the TTL is
        # only a cleanup hint; tests never accumulate enough keys to matter.
        count = self._counts.get(key, 0) + 1
        self._counts[key] = count
        return count
