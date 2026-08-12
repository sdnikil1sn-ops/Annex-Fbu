"""Unit tests for analysis-repository helpers (no database required).

The PostgreSQL repository is exercised against a real database in
``tests/integration/test_analysis_repository.py``; these tests cover the
psycopg adaptation wiring that would otherwise only fail at runtime there.
"""

from app.infrastructure.repositories.analysis_repository import _report_param
from psycopg.types.json import Jsonb


def test_report_param_wraps_dicts_for_jsonb() -> None:
    """A report dict must be wrapped in Jsonb for psycopg adaptation.

    psycopg does not adapt plain ``dict`` to ``jsonb`` automatically; the
    wrapper is what makes the column write work.
    """
    wrapped = _report_param({"summary": "s", "claims": []})
    assert isinstance(wrapped, Jsonb)
    assert wrapped.obj == {"summary": "s", "claims": []}


def test_report_param_preserves_sql_null_when_absent() -> None:
    """No report must stay SQL NULL, not a jsonb 'null' value."""
    assert _report_param(None) is None
