"""Repository implementations (ADR-0003).

Concrete persistence behind the ports in app.application.ports. All SQL is
parameterized — never assembled from string interpolation (SECURITY.md).
"""
