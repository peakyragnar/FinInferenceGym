"""Tests for mechanisms/lints/no_alpha_features.py.

The lint enforces DESIGN.md Layer 0: derived evidence is mechanical
transformation, not alpha cognition. These tests verify it catches the
intended failure modes (alpha-flavored compound names) and does not
catch the legitimate cases (verifier scoring math, override-marked
mechanical transformations, out-of-scope files).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT_PATH = REPO_ROOT / "mechanisms" / "lints" / "no_alpha_features.py"


def _load_lint_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("no_alpha_features", LINT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load_lint_module()


# --- check_file: positive cases (should flag) ---------------------------


def test_flags_quality_score(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("quality_score: float = 0.0\n")
    violations = lint.check_file(f)
    assert len(violations) == 1
    assert violations[0][2].lower() == "quality_score"


def test_flags_value_premium_in_dataclass(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("class FactorRow:\n    value_premium: float\n")
    violations = lint.check_file(f)
    assert len(violations) == 1


def test_flags_case_insensitive(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("MomentumScore = 0  # nope\nQuality_Rank: int = 1\n")
    violations = lint.check_file(f)
    # MomentumScore (no underscore) is NOT on the denylist; Quality_Rank IS.
    assert len(violations) == 1
    assert violations[0][2].lower() == "quality_rank"


def test_flags_substring_inside_compound_name(tmp_path: Path) -> None:
    """A function named compute_quality_score is still flagged because the
    alpha-feature concept is embedded in the name. The right fix is to rename."""
    f = tmp_path / "f.py"
    f.write_text("def compute_quality_score():\n    pass\n")
    violations = lint.check_file(f)
    assert len(violations) == 1


# --- check_file: negative cases (should NOT flag) -----------------------


def test_skips_line_with_override_marker(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text(
        "quality_score: float = 0.0  # derived-evidence-allow: legacy column from vendor schema\n"
    )
    violations = lint.check_file(f)
    assert violations == []


def test_does_not_flag_brier_score(tmp_path: Path) -> None:
    """brier_score and log_score are scoring functions in the verifier; they
    are NOT alpha features. They are not on the denylist."""
    f = tmp_path / "f.py"
    f.write_text(
        "def brier_score(belief, outcome):\n    return 0.0\n"
        "def log_score(belief, outcome):\n    return 0.0\n"
    )
    violations = lint.check_file(f)
    assert violations == []


def test_does_not_flag_unrelated_identifiers(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text(
        "as_of: datetime\n"
        "as_known: datetime\n"
        "transcript_speaker_turn: str\n"
        "edge_calculator = None  # 'edge' alone is project vocabulary\n"
    )
    violations = lint.check_file(f)
    assert violations == []


# --- _in_scope: scope filtering -----------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "src/fingym/data/foo.py",
        "src/fingym/agents/bar.py",
        "src/fingym/beliefs/baz.py",
        "src/fingym/memory/qux.py",
        "migrations/versions/0001_init.py",
    ],
)
def test_in_scope_includes_production_paths(path: str) -> None:
    assert lint._in_scope(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "src/fingym/evaluator/scoring.py",
        "src/fingym/toys/coin.py",
        "tests/unit/test_x.py",
        "mechanisms/lints/no_alpha_features.py",
        "docs/random.py",
        "scripts/oneoff.py",
    ],
)
def test_in_scope_excludes_off_limits_paths(path: str) -> None:
    assert lint._in_scope(path) is False


# --- main: end-to-end with cwd ------------------------------------------


def test_main_returns_nonzero_on_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "fingym" / "data" / "leak.py"
    target.parent.mkdir(parents=True)
    target.write_text("growth_factor: float = 0.0\n")
    rc = lint.main(["src/fingym/data/leak.py"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "growth_factor" in captured.err


def test_main_returns_zero_on_clean_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "fingym" / "data" / "clean.py"
    target.parent.mkdir(parents=True)
    target.write_text("as_of: str\n")
    rc = lint.main(["src/fingym/data/clean.py"])
    assert rc == 0


def test_main_skips_out_of_scope_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if the file contains a banned name, it is silently skipped when
    out of scope (e.g., evaluator/, toys/, tests/)."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "fingym" / "evaluator" / "scoring.py"
    target.parent.mkdir(parents=True)
    target.write_text("quality_score: float = 0.0\n")
    rc = lint.main(["src/fingym/evaluator/scoring.py"])
    assert rc == 0


def test_main_handles_no_files() -> None:
    assert lint.main([]) == 0


# Cleanup module from sys.modules to avoid leaking across test sessions.
def teardown_module() -> None:
    sys.modules.pop("no_alpha_features", None)
