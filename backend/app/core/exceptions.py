"""Shared exceptions for infrastructure configuration failures."""


class ConfigurationError(Exception):
    """Raised when an external integration cannot be initialized.

    Used by adapters whose prerequisites are missing (Firebase credentials,
    the Tesseract binary, provider keys, ...) so callers fail fast with a
    clear, actionable message instead of a confusing runtime error.
    """
