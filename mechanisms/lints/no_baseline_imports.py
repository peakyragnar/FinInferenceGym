#!/usr/bin/env python3
"""Pre-commit lint: forbid imports of `fingym.baseline` outside src/fingym/baseline/.

Enforces DESIGN.md commitment #10 / PYRAMID Stone 11e: the Market-State
Baseline (Track C) is a separately-isolated module. The AI Core, the
agent layer, the memory pyramid, the action engine, the forecast ledger,
and the evaluator MUST NOT see the Baseline's processed forecast — only
the Scoreboard sees both AI and Baseline outputs side by side as
separate columns.

Why this matters:
    - If the AI could read the Baseline's forecast, three failure modes:
        1. Leakage — AI copies the Baseline's forecast
        2. Anchoring — AI conditions on the Baseline's confidence
        3. Coordination — AI deliberately differentiates from the Baseline
    - The `incremental_AI_edge = AI realized edge - Baseline realized edge`
      attribution column is meaningful only if the two are independent.

The harness-engineering principle: enforce by mechanism, not prompt.
Discipline alone fails silently as the codebase grows; the lint fails
loudly at commit time.

Usage:
    Configured in .pre-commit-config.yaml as a local hook.
    Receives staged Python files as arguments.
    Returns non-zero exit code on violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Forbidden import statements outside the baseline/ package.
FORBIDDEN_IMPORTS = re.compile(r"^\s*(?:from|import)\s+(fingym\.baseline)(?:\s|\.|$)")

# The Baseline package; the only legitimate location for `fingym.baseline` imports.
ALLOWED_PREFIX = "src/fingym/baseline/"

# Test code is exempt — integration tests legitimately import both AI and
# Baseline to verify they produce paired outputs on the Scoreboard.
EXEMPT_PREFIXES: tuple[str, ...] = ("tests/",)


def check_file(path: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations
    for i, line in enumerate(text.splitlines(), start=1):
        if FORBIDDEN_IMPORTS.match(line):
            violations.append((i, line.rstrip()))
    return violations


def main(argv: list[str]) -> int:
    failed = False
    for arg in argv:
        if arg.startswith(ALLOWED_PREFIX):
            continue
        if any(arg.startswith(p) for p in EXEMPT_PREFIXES):
            continue
        path = Path(arg)
        if path.suffix != ".py":
            continue
        violations = check_file(path)
        for line_no, line in violations:
            print(
                f"{path}:{line_no}: import of fingym.baseline forbidden "
                f"outside src/fingym/baseline/.",
                file=sys.stderr,
            )
            print(f"    {line}", file=sys.stderr)
            failed = True

    if failed:
        print(
            "\n"
            "DESIGN.md #10 / PYRAMID Stone 11e — Market-State Baseline isolation.\n"
            "The AI Core MUST NOT see the Baseline's processed forecast.\n"
            "The two modules meet only at the Scoreboard, where their outputs\n"
            "are scored side by side as separate agent_id-distinguished rows.\n"
            "The Scoreboard.incremental_AI_edge helper computes attribution.\n",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
