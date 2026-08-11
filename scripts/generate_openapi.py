#!/usr/bin/env python3
"""Generate ``docs/api/openapi.yaml`` from the FastAPI application.

The generated file is the executable API contract (ADR-0002): clients and
the ``shared_models`` codegen pipeline derive their types from it.

Requires the backend to be installed in the active environment:

    cd backend && ../.venv/Scripts/python -m pip install -e ".[dev]"

Usage:
    .venv/Scripts/python scripts/generate_openapi.py   # native Windows
    .venv/bin/python scripts/generate_openapi.py       # POSIX shells
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.yaml"


def main() -> int:
    """Dump the application's OpenAPI schema to the documentation tree."""
    from app.core.config import Settings
    from app.main import create_app

    # Deterministic generation: test environment, no .env side effects.
    app = create_app(Settings(_env_file=None, app_env="test"))
    spec = app.openapi()

    OUTPUT.write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(
        f"Wrote OpenAPI spec ({len(spec['paths'])} paths) "
        f"to {OUTPUT.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
