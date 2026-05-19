"""Shared pytest setup for FinInferenceGym tests.

Loads `.env` into `os.environ` if present and the variable isn't already
set in the shell. Zero external deps — reads the file directly so we
don't pull in `python-dotenv` for one feature.

Tests that depend on external services (e.g., Cluster F's Anthropic API
calls) use `pytest.mark.skipif(not os.environ.get(...))` and skip when
the variable is missing. With this conftest, the variable becomes
available from `.env` automatically; no need to `export` it manually.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_env_file_if_present() -> None:
    """Populate os.environ from `.env` at the project root.

    A NON-EMPTY shell value wins over `.env` (so an explicit `export` from
    the shell takes precedence). But an EMPTY shell value (e.g.,
    `export ANTHROPIC_API_KEY=` lingering from a prior session) does NOT
    block the `.env` value — empty/blank shell values are treated as
    "unset" and replaced. Blank `.env` values are skipped. Silently noops
    if `.env` is missing.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Strip inline comments and surrounding whitespace; keep quoted values verbatim.
        value = value.split("#", 1)[0].strip().strip("\"'")
        if not key or not value:
            continue
        # Override empty/blank shell values; respect non-empty ones.
        existing = os.environ.get(key, "").strip()
        if not existing:
            os.environ[key] = value


_load_env_file_if_present()
