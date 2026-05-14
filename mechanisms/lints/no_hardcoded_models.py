#!/usr/bin/env python3
"""Pre-commit lint: forbid direct LLM SDK imports outside src/fingym/llm/.

Enforces DESIGN.md commitment #7: Intelligence lives in architecture, not
weights or prompts. Models are swappable engines. Memory, hypothesis
registry, evaluator, and promotion gate are all model-agnostic.

The model swap layer at src/fingym/llm/ is the only place that imports a
specific LLM provider's SDK. Code outside this layer goes through the
typed model-interface contract (src/fingym/llm/contract.py).

Why this matters:
    - If LLM SDK imports leak outside src/fingym/llm/, model swapping
      becomes a code change instead of a config change.
    - This defeats DESIGN.md #7 and locks the system to one model.
    - The harness-engineering principle: enforce by mechanism, not prompt.

Usage:
    Configured in .pre-commit-config.yaml as a local hook.
    Receives staged Python files as arguments.
    Returns non-zero exit code on violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Forbidden import statements outside the llm/ package.
FORBIDDEN_IMPORTS = re.compile(
    r"^\s*(?:from|import)\s+("
    r"anthropic"
    r"|openai"
    r"|google\.genai"
    r"|google_genai"
    r"|google\.generativeai"
    r")(?:\s|\.|$)"
)

# The model swap layer; the only legitimate location for direct SDK imports.
ALLOWED_PREFIX = "src/fingym/llm/"

# Test code is exempt (mocks, fixtures may instantiate SDK types).
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
                f"{path}:{line_no}: direct LLM SDK import forbidden outside src/fingym/llm/.",
                file=sys.stderr,
            )
            print(f"    {line}", file=sys.stderr)
            failed = True

    if failed:
        print(
            "\n"
            "DESIGN.md #7 — Intelligence in architecture, not weights or prompts.\n"
            "All model access goes through src/fingym/llm/ (the model swap "
            "layer) so model choice remains a config change, not a code change.\n"
            "Use:  from fingym.llm.contract import ModelClient\n",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
