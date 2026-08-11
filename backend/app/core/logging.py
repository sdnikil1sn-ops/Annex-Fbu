"""Structured logging setup.

A single configuration point that formats log records with the active
request ID so every log line can be correlated with an HTTP request. The
request ID lives in a ``ContextVar`` populated by the request-id middleware
(see ``app.core.request_id``).
"""

import logging
import sys
from contextvars import ContextVar

# Shared request-ID slot: written by the middleware, read by the formatter.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFormatter(logging.Formatter):
    """Log formatter that injects the current request ID into every record."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record, attaching ``request_id`` as a record attribute."""
        record.request_id = request_id_var.get()
        return super().format(record)


def configure_logging(level: str, *, debug: bool = False) -> None:
    """Configure root logging for the application.

    Args:
        level: Logging level name (``DEBUG``, ``INFO``, ``WARNING``, ...).
        debug: When true, force the level to DEBUG regardless of ``level``.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RequestIdFormatter(
            "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel("DEBUG" if debug else level.upper())
