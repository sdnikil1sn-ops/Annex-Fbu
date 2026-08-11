#!/usr/bin/env python3
"""ANNEX repository validation script.

Validates the repository foundation on every run, locally and in CI:

    1. YAML syntax    -- every .yml/.yaml file must parse cleanly.
    2. Markdown links -- every internal relative link must resolve to a file.
    3. Required files -- the foundation files mandated by Phase 1 must exist.
    4. Secret patterns -- obvious credential material must not be committed.

Exit codes:
    0 -- all checks passed (YAML check may be skipped if PyYAML is missing)
    1 -- at least one check failed

Usage:
    python scripts/validate_repo.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Repository root is two levels up from this file: scripts/ -> repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that are never part of repository validation.
IGNORED_DIRS: set[str] = {
    ".git",
    "node_modules",
    ".dart_tool",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "dist",
    ".idea",
    ".vscode",
    ".gradle",
}

# Foundation files that must exist at the repository root (Phase 1 contract).
REQUIRED_ROOT_FILES: list[str] = [
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
]

# Binary/asset extensions skipped by the secret scan.
BINARY_SUFFIXES: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".pdf", ".zip", ".gz", ".woff", ".woff2", ".ttf", ".otf",
    ".jar", ".aab", ".apk", ".ipa", ".keystore", ".jks",
}

# Patterns that indicate committed secrets (deliberately conservative).
SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),        # OpenAI-style API keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),           # AWS access key IDs
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),        # GitHub personal access tokens
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),      # Google/Firebase API keys
]

ERRORS: list[str] = []


def walk_files() -> list[Path]:
    """Return every repository file, skipping ignored directories."""
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        files.append(path)
    return files


def check_required_files() -> None:
    """Verify the Phase 1 foundation files exist at the repository root."""
    for name in REQUIRED_ROOT_FILES:
        if not (REPO_ROOT / name).exists():
            ERRORS.append(f"[FILES] missing required root file: {name}")
    print(f"[ OK ] Files: {len(REQUIRED_ROOT_FILES)} required root file(s) checked")


def check_yaml(files: list[Path]) -> None:
    """Parse every YAML file; record syntax errors."""
    try:
        import yaml  # PyYAML; CI installs it, local install documented
    except ImportError:
        print("[SKIP] YAML check: PyYAML is not installed "
              "(run: python -m venv .venv && .venv/bin/python -m pip install pyyaml)")
        return

    checked = 0
    for path in files:
        if path.suffix.lower() not in {".yml", ".yaml"}:
            continue
        checked += 1
        try:
            with path.open("r", encoding="utf-8") as handle:
                for _ in yaml.safe_load_all(handle):
                    pass
        except yaml.YAMLError as exc:
            ERRORS.append(f"[YAML] {path.relative_to(REPO_ROOT)}: {exc}")
    print(f"[ OK ] YAML: {checked} file(s) parsed")


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_markdown_links(files: list[Path]) -> None:
    """Verify every internal relative link inside .md files resolves."""
    checked = 0
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#")[0].strip()
            if not clean:
                continue
            if not (path.parent / clean).resolve().exists():
                ERRORS.append(f"[LINK] {path.relative_to(REPO_ROOT)} -> {target}")
    print(f"[ OK ] Links: {checked} markdown file(s) checked")


def check_secrets(files: list[Path]) -> None:
    """Scan text files for obvious committed-secret patterns."""
    checked = 0
    for path in files:
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        checked += 1
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                ERRORS.append(
                    f"[SECRET] {path.relative_to(REPO_ROOT)}: "
                    f"matched {pattern.pattern[:40]}..."
                )
                break
    print(f"[ OK ] Secrets: {checked} file(s) scanned")


def main() -> int:
    """Run all checks and return the process exit code."""
    print(f"ANNEX repository validation -- root: {REPO_ROOT}")
    files = walk_files()
    check_required_files()
    check_yaml(files)
    check_markdown_links(files)
    check_secrets(files)

    if ERRORS:
        print("\nValidation FAILED:")
        for error in ERRORS:
            print(f"  - {error}")
        return 1

    print("\nValidation PASSED: repository is healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
