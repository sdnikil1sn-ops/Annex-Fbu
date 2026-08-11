"""HTTP API layer: routers, dependencies, and error handling.

Routers stay thin (validation, auth, serialization) and delegate all
business logic to the application layer (ADR-0003). Error responses are
normalized into a single machine-readable envelope.
"""
