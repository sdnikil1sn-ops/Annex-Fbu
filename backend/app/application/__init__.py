"""Application layer — use cases and service classes (ADR-0003).

This layer contains the business workflows of ANNEX (analysis submission,
report retrieval, source scoring, ...). Services are injectable classes
that depend on ports and repositories, never on routers or external SDKs.
Populated from Phase 4 onward.
"""
