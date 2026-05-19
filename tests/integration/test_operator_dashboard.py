"""Operator dashboard integration test.

Verifies the read-only operator view (`uv run python -m fingym.operator
report`) correctly surfaces Scoreboard, attribution, memory, and gate-
log sections.

The test:
  1. Builds a synthetic Scoreboard with rows from two agents (a Bayesian
     "AI" and the Market-State Baseline), writes it to a tmp_path JSONL
     via the new scoreboard_io.append_row.
  2. Builds two MemoryArtifacts (one L3 promoted, one L2 probationary)
     and writes them to tmp_path/promoted and tmp_path/probationary.
  3. Invokes the CLI as a subprocess pointing at those paths.
  4. Asserts the output contains the expected section headers and key
     data points.

Smoke-level: validates the report's plumbing (data → file → CLI → text
output). Detailed per-section formatting is exercised by `report.py`
itself, not asserted here.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fingym.agents.contract import NoAction, TradeAction
from fingym.baseline.market_state import BASELINE_AGENT_ID
from fingym.evaluator.scoreboard import ScoreboardRow
from fingym.evaluator.scoreboard_io import append_row, load_scoreboard
from fingym.memory.schema import (
    AuditEntry,
    CrossModelRegressionResult,
    DomainOfValidity,
    HeldOutReplayResult,
    MemoryArtifact,
    PromotionCheckResults,
    SurvivorshipCheckResult,
)
from fingym.memory.storage import save_probationary_skill, save_promoted_skill


def _trade_row(
    agent_id: str,
    realized_return: float,
    realized_edge: float,
    brier: float = 0.20,
) -> ScoreboardRow:
    """Build a TradeAction ScoreboardRow with the minimal fields needed
    for serialization round-trip + report rendering."""
    return ScoreboardRow(
        agent_id=agent_id,
        signal_class_id="test_sci",
        horizon=1,
        decision_time=datetime(2026, 5, 18, 12, 0, 0),
        forecast_distribution={
            "below_minus_5": 0.05,
            "minus_5_to_0": 0.10,
            "zero_to_plus_5": 0.20,
            "plus_5_to_plus_10": 0.40,
            "above_plus_10": 0.25,
        },
        calibrated_forecast={
            "below_minus_5": 0.05,
            "minus_5_to_0": 0.10,
            "zero_to_plus_5": 0.20,
            "plus_5_to_plus_10": 0.40,
            "above_plus_10": 0.25,
        },
        calibrated_expected_return=0.04,
        calibrated_expected_utility=0.03,
        tradable_edge_score=0.02,
        kelly_fraction_applied=0.25,
        final_action=TradeAction(
            expression_type="equity-long",
            underlying="TOY",
            direction="long",
            size=100,
            notional=10_000.0,
        ),
        realized_return=realized_return,
        realized_bucket="zero_to_plus_5",
        brier=brier,
        log_score=0.5,
        realized_edge=realized_edge,
    )


def _no_action_row(agent_id: str, brier: float = 0.30) -> ScoreboardRow:
    return ScoreboardRow(
        agent_id=agent_id,
        signal_class_id="test_sci",
        horizon=1,
        decision_time=datetime(2026, 5, 18, 12, 0, 0),
        forecast_distribution={
            "below_minus_5": 0.20,
            "minus_5_to_0": 0.20,
            "zero_to_plus_5": 0.20,
            "plus_5_to_plus_10": 0.20,
            "above_plus_10": 0.20,
        },
        calibrated_forecast={
            "below_minus_5": 0.20,
            "minus_5_to_0": 0.20,
            "zero_to_plus_5": 0.20,
            "plus_5_to_plus_10": 0.20,
            "above_plus_10": 0.20,
        },
        calibrated_expected_return=0.0,
        calibrated_expected_utility=-0.005,
        tradable_edge_score=-0.015,
        kelly_fraction_applied=0.0,
        final_action=NoAction(reason="below threshold"),
        realized_return=0.02,
        realized_bucket="zero_to_plus_5",
        brier=brier,
        log_score=1.6,
        realized_edge=0.0,
    )


def test_scoreboard_io_jsonl_roundtrip(tmp_path: Path) -> None:
    """Write three rows to a JSONL file, then load them back. The
    reconstructed Scoreboard must match the original by agent counts,
    final_action type, and key numeric fields."""
    path = tmp_path / "scoreboard.jsonl"
    r1 = _trade_row("bayesian_agent", realized_return=0.03, realized_edge=0.022)
    r2 = _trade_row(BASELINE_AGENT_ID, realized_return=0.03, realized_edge=0.012)
    r3 = _no_action_row("bayesian_agent")

    for row in (r1, r2, r3):
        append_row(row, path)

    sb = load_scoreboard(path)
    assert sb.total_rows() == 3
    bayesian = sb.filter_by_agent("bayesian_agent")
    baseline = sb.filter_by_agent(BASELINE_AGENT_ID)
    assert len(bayesian) == 2
    assert len(baseline) == 1

    # Action types survive the round trip.
    assert isinstance(bayesian[0].final_action, TradeAction)
    assert isinstance(bayesian[1].final_action, NoAction)
    assert isinstance(baseline[0].final_action, TradeAction)

    # Numeric fields survive.
    assert bayesian[0].realized_edge == 0.022
    assert baseline[0].realized_edge == 0.012


def test_scoreboard_io_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """Loading from a missing path returns an empty Scoreboard rather
    than crashing (so the dashboard can print 'no data yet' cleanly)."""
    sb = load_scoreboard(tmp_path / "does_not_exist.jsonl")
    assert sb.total_rows() == 0


def _make_l3_artifact(artifact_id: str, content: str) -> MemoryArtifact:
    now = datetime(2026, 5, 18, 14, 0, 0)
    return MemoryArtifact(
        id=artifact_id,
        tier="L3",
        content=content,
        domain_of_validity=DomainOfValidity(horizons=["1", "3"]),
        derived_from=[],
        audit_trail=[
            AuditEntry(
                timestamp=now,
                action="proposed",
                by="test_agent",
                reason="Episode 1; test proposal.",
            ),
            AuditEntry(
                timestamp=now,
                action="promoted",
                by="system",
                reason="Test promotion via gate.",
            ),
        ],
        promotion_check_results=PromotionCheckResults(
            held_out_replay=HeldOutReplayResult(
                passed=True, splits_passed=1, calibration_delta=0.25
            ),
            cross_model_regression=CrossModelRegressionResult(
                passed=True, models_validated=["agent_a", "agent_b"]
            ),
            survivorship_check=SurvivorshipCheckResult(passed=False, delisted_sample_size=0),
            domain_of_validity_declared=True,
        ),
        promoted_at=now,
    )


def _make_l2_artifact(artifact_id: str, content: str) -> MemoryArtifact:
    now = datetime(2026, 5, 18, 14, 0, 0)
    return MemoryArtifact(
        id=artifact_id,
        tier="L2",
        content=content,
        domain_of_validity=DomainOfValidity(horizons=["1"]),
        derived_from=[],
        audit_trail=[
            AuditEntry(
                timestamp=now,
                action="proposed",
                by="test_agent",
                reason="Probationary candidate.",
            ),
        ],
    )


def _run_report(
    scoreboard_path: Path,
    l3_dir: Path,
    l2_dir: Path,
) -> subprocess.CompletedProcess[str]:
    """Invoke the operator CLI as a subprocess. Returns the completed
    process so the caller can assert on returncode / stdout / stderr."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fingym.operator",
            "report",
            "--scoreboard-path",
            str(scoreboard_path),
            "--l3-dir",
            str(l3_dir),
            "--l2-dir",
            str(l2_dir),
        ],
        capture_output=True,
        text=True,
    )


def test_operator_report_empty_state_renders_cleanly(tmp_path: Path) -> None:
    """With no scoreboard rows and no memory artifacts, the report
    prints empty-state markers rather than crashing."""
    result = _run_report(
        scoreboard_path=tmp_path / "scoreboard.jsonl",
        l3_dir=tmp_path / "promoted",
        l2_dir=tmp_path / "probationary",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = result.stdout
    assert "Operator Report" in out
    assert "[1] Scoreboard summary" in out
    assert "no Scoreboard rows" in out
    assert "[2] Track C attribution" in out
    assert "[3] Memory state" in out
    assert "L3 promoted (0)" in out
    assert "L2 probationary (0)" in out
    assert "[4] Recent gate activity" in out
    assert "no gate activity yet" in out


def test_operator_report_full_state_renders_each_section(tmp_path: Path) -> None:
    """With a populated Scoreboard + L3 + L2, each section surfaces the
    expected agent IDs, attribution number, and skill IDs."""
    # Build a Scoreboard with rows for two agents.
    scoreboard_path = tmp_path / "scoreboard.jsonl"
    rows = [
        _trade_row("bayesian_agent", realized_return=0.05, realized_edge=0.030),
        _trade_row("bayesian_agent", realized_return=0.04, realized_edge=0.025),
        _trade_row(BASELINE_AGENT_ID, realized_return=0.05, realized_edge=0.010),
        _trade_row(BASELINE_AGENT_ID, realized_return=0.04, realized_edge=0.012),
    ]
    for row in rows:
        append_row(row, scoreboard_path)

    # Build + save one L3 and one L2 artifact.
    l3_dir = tmp_path / "promoted"
    l2_dir = tmp_path / "probationary"
    l3_artifact = _make_l3_artifact(
        "majority_strong_abc12345",
        "When 4 or more of the most recent 6 signals are STRONG, expect upside.",
    )
    l2_artifact = _make_l2_artifact(
        "weak_streak_xyz78901",
        "Three consecutive WEAK signals predict downside at 1-month horizon.",
    )
    save_promoted_skill(l3_artifact, l3_dir)
    save_probationary_skill(l2_artifact, l2_dir)

    result = _run_report(scoreboard_path, l3_dir, l2_dir)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = result.stdout

    # Header line shows row counts
    assert "4 rows" in out
    assert "1 promoted skills" in out
    assert "1 probationary skills" in out

    # Section 1: Scoreboard summary shows both agents
    assert "bayesian_agent" in out
    assert BASELINE_AGENT_ID in out

    # Section 2: Track C attribution computes mean(bayesian) - mean(baseline)
    # = mean(0.030, 0.025) - mean(0.010, 0.012) = 0.0275 - 0.011 = +0.0165
    assert "+0.0165" in out or "0.016" in out or "+0.017" in out

    # Section 3: Memory state surfaces the skill IDs
    assert "majority_strong_abc12345" in out
    assert "weak_streak_xyz78901" in out

    # Section 4: Gate activity surfaces audit_trail entries
    assert "promoted" in out  # L3's audit entry
    assert "proposed" in out  # L2's (and L3's) audit entry


def test_operator_report_loads_from_default_paths_safely(tmp_path: Path) -> None:
    """The CLI accepts default paths and doesn't crash if those paths
    don't exist (most importantly when run from a fresh checkout)."""
    # Run from inside tmp_path so the default paths
    # (data_cache/scoreboard.jsonl, memory_registry/promoted, etc.)
    # all resolve to non-existent locations.
    result = subprocess.run(
        [sys.executable, "-m", "fingym.operator", "report"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Operator Report" in result.stdout
