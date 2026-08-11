"""Cross-cutting core: configuration, logging, and request tracing.

This package holds concerns shared by every other layer (config, logging,
middleware). It must not import from api, application, domain, or
infrastructure (dependency rule, ADR-0003).
"""
