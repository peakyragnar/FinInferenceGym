#!/usr/bin/env python3
"""Pre-commit lint: forbid hand-coded alpha-feature names in production code.

Enforces DESIGN.md commitment #5/#6 and the Layer 0 derived-evidence
distinction: the data spine and agent code paths must not contain
hand-coded alpha cognition disguised as derived features. The verifier
may encode physics (Bayes, Kelly, proper scoring); the verifier may not
encode alpha (factor scores, sentiment ranks, conviction premiums).

Anything labeled "score," "rank," "premium," "factor," "signal," or
"quality" in a compound identifier is alpha cognition and belongs in the
model, not in the spine. This lint is a tripwire targeting the
historical factor-model vocabulary; it is not airtight and is not meant
to be. The principle holds in code review for the rest.

Scope:
  - INCLUDE: src/fingym/ (except evaluator/ and toys/), migrations/
  - EXCLUDE: src/fingym/evaluator/ (verification side; "score" is legit
    scoring math), src/fingym/toys/ (legitimate fixtures), tests/,
    mechanisms/.

Override marker (per line): include the substring
"derived-evidence-allow:" anywhere on the same line. Use sparingly and
only when the identifier is a mechanical transformation, not alpha
cognition.

Usage (via pre-commit framework):
    Configured in .pre-commit-config.yaml as a local hook.
    Receives staged Python files as arguments.
    Returns non-zero exit code on violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Compound identifier names from the historical quant-alpha vocabulary.
# Substring match, case-insensitive. Extending this list requires a
# DECISIONS.md entry; weakening it (removing entries) requires a
# DECISIONS.md entry plus Michael sign-off, since the list IS the
# enforcement.
ALPHA_FEATURE_NAMES: tuple[str, ...] = (
    "quality_score",
    "quality_rank",
    "quality_factor",
    "quality_premium",
    "value_score",
    "value_premium",
    "value_factor",
    "value_rank",
    "growth_premium",
    "growth_factor",
    "growth_score",
    "momentum_score",
    "momentum_signal",
    "momentum_factor",
    "tone_score",
    "sentiment_score",
    "sentiment_factor",
    "founder_premium",
    "management_score",
    "disruption_factor",
    "disruption_premium",
    "conviction_score",
    "conviction_rank",
    "cheapness_rank",
    "cheapness_score",
)

PATTERN = re.compile(
    "|".join(re.escape(name) for name in ALPHA_FEATURE_NAMES),
    re.IGNORECASE,
)

INCLUDE_PREFIXES: tuple[str, ...] = (
    "src/fingym/",
    "migrations/",
)

EXCLUDE_PREFIXES: tuple[str, ...] = (
    "src/fingym/evaluator/",
    "src/fingym/toys/",
)

OVERRIDE_MARKER = "derived-evidence-allow:"


def _in_scope(arg: str) -> bool:
    if not any(arg.startswith(prefix) for prefix in INCLUDE_PREFIXES):
        return False
    if any(arg.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
        return False
    return True


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Return a list of (line_number, line, matched_token) violations."""
    violations: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations

    for i, line in enumerate(text.splitlines(), start=1):
        if OVERRIDE_MARKER in line:
            continue
        match = PATTERN.search(line)
        if match:
            violations.append((i, line.rstrip(), match.group(0)))
    return violations


def main(argv: list[str]) -> int:
    failed = False
    for arg in argv:
        if not _in_scope(arg):
            continue
        path = Path(arg)
        if path.suffix != ".py":
            continue
        violations = check_file(path)
        for line_no, line, token in violations:
            print(
                f"{path}:{line_no}: forbidden alpha-feature name '{token}' "
                "(DESIGN.md Layer 0 — derived evidence is mechanical "
                "transformation, not alpha cognition).",
                file=sys.stderr,
            )
            print(f"    {line}", file=sys.stderr)
            failed = True

    if failed:
        print(
            "\n"
            "Hand-coded alpha-feature names are forbidden in the data spine\n"
            "and agent code paths. Anything labeled 'score', 'rank', 'premium',\n"
            "'factor', 'signal', or 'quality' is alpha cognition and belongs\n"
            "in the model, not in the spine.\n"
            "\n"
            "If this is a legitimate mechanical transformation (not alpha),\n"
            "rename it to remove the alpha-flavored token, OR add the marker\n"
            f"'{OVERRIDE_MARKER} <reason>' on the same line.\n"
            "\n"
            "Removing entries from ALPHA_FEATURE_NAMES or weakening this lint\n"
            "requires a DECISIONS.md entry and Michael sign-off.\n",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
