"""Infrastructure layer — repositories and external adapters (ADR-0003).

Implements the ports the application layer depends on: Supabase/PostgreSQL
repositories, Redis caches, Firebase verification, and AI-provider
adapters. All infrastructure is swappable behind ports. Populated from
Phase 4 onward.
"""
