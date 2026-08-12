"""Redis-backed rate limiting (Phase 7).

``limiter.py`` defines fixed-window limits parsed from ``"<count>/<unit>"``
settings; ``store.py`` provides Redis and in-memory counter stores; the
ASGI ``middleware.py`` enforces limits per client + endpoint scope; and
``factory.py`` selects the implementation from settings with a no-op
fallback when Redis is not configured.
"""
