"""ANNEX backend application package.

The FastAPI service follows the layered architecture defined in ADR-0003:

    api (routers) -> application (services) -> domain -> infrastructure

Phase 3 delivers the application core — configuration, structured logging,
request tracing, the error envelope, and the system endpoints. The
application, domain, and infrastructure layers are populated in later
phases (database: 4, auth: 5, AI: 6, caching/jobs: 7).
"""

__version__ = "0.1.0"
