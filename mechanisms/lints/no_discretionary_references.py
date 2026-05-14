#!/usr/bin/env python3
"""Pre-commit lint: forbid Michael/discretionary references in production code.

Enforces DESIGN.md commitment #10: Michael is the auditor only — not a
calibration input, training signal, or baseline. Using his discretionary
calls as a comparison anchor (even as "just diagnostics") smuggles his
bias into the system's loss function.

This lint catches the specific failure mode by name. Production code in
src/fingym/ must not reference Michael, his views, or his trades.

Usage (via pre-commit framework):
    Configured in .pre-commit-config.yaml as a local hook.
    Receives staged Python files as arguments.
    Returns non-zero exit code on violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that indicate discretionary-trader bias-import.
FORBIDDEN_PATTERNS: list[str] = [
    r"\bmichael\b",
    r"\bdiscretionary\b",
    r"\bmy_trade\w*",
    r"\bmy_position\w*",
    r"\bmy_view\w*",
    r"\bagreement_matrix\b",
    r"\bdisagreement_matrix\b",
    r"\bhuman_baseline\b",
    r"\boperator_signal\b",
]

PATTERN = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)

# Production code that this lint enforces.
PRODUCTION_PREFIX = "src/fingym/"

# Allowed substring exceptions — comments referencing the rule itself.
ALLOWED_REFERENCE_MARKERS: tuple[str, ...] = (
    "no_discretionary_references",
    "DESIGN.md #10",
    "DESIGN.md commitment #10",
)


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Return a list of (line_number, line, matched_token) violations."""
    violations: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations

    for i, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in ALLOWED_REFERENCE_MARKERS):
            continue
        match = PATTERN.search(line)
        if match:
            violations.append((i, line.rstrip(), match.group(0)))
    return violations


def main(argv: list[str]) -> int:
    failed = False
    for arg in argv:
        if not arg.startswith(PRODUCTION_PREFIX):
            continue
        path = Path(arg)
        if path.suffix != ".py":
            continue
        violations = check_file(path)
        for line_no, line, token in violations:
            print(
                f"{path}:{line_no}: forbidden reference '{token}' "
                "(DESIGN.md #10 — Michael is the auditor only).",
                file=sys.stderr,
            )
            print(f"    {line}", file=sys.stderr)
            failed = True

    if failed:
        print(
            "\n"
            "Discretionary / Michael references are forbidden in production code.\n"
            "Use domain-neutral terms: 'agent_belief' not 'my_view', "
            "'comparison_baseline' not 'michael_baseline'.\n"
            "If this is a legitimate exception (e.g., a docstring quoting "
            "DESIGN.md), include the marker 'DESIGN.md #10' on the same line.\n"
            "Removing this lint or expanding its exceptions requires a "
            "DECISIONS.md entry.\n",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
