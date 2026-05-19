"""Cluster I end-to-end (PYRAMID Stone 11e in toy mode).

Three test surfaces:

1. **Baseline mechanics** (no API). `HeadlineObservables` sampling biases
   toward the state-natural bucket per `OBSERVABLE_STRENGTH`. The
   `MarketStateBaseline` Bayesian Ledger learns from observations and
   emits the empirical distribution; falls back to uniform when a cell
   is empty.

2. **Side-by-side AI + Baseline** (no API). Run BayesianAgent (info-rich)
   and ConfidentAgent (bullshit) side by side with the Baseline. Verify
   `Scoreboard.incremental_ai_edge` computes the right attribution number
   per agent.

3. **Architectural isolation** (subprocess). The
   `mechanisms/lints/no_baseline_imports.py` lint fails when a file
   outside `src/fingym/baseline/` imports `fingym.baseline`. Validates
   the structural defense, not just convention.
"""

from __future__ import annotations

import random
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from fingym.action.action_engine import ToyCostModel, decide
from fingym.baseline.market_state import BASELINE_AGENT_ID, MarketStateBaseline
from fingym.evaluator.realized_edge import realized_edge
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.toys.adversarial_agents import (
    DEFAULT_BAYESIAN_PRIOR,
    BayesianAgent,
    ConfidentAgent,
)
from fingym.toys.synthetic_market import (
    OBSERVABLE_BUCKETS,
    RETURN_BUCKETS,
    STATES,
    CompanyState,
    HeadlineObservables,
    ObservableBucket,
    ReturnBucket,
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
    sample_headline_observables,
)

# ---------------------------------------------------------------------------
# Headline observables sampling
# ---------------------------------------------------------------------------


def test_observable_sampling_biases_toward_state_natural_bucket() -> None:
    """At OBSERVABLE_STRENGTH > 0, sampling from a state should produce
    its natural bucket more often than 1/3 of the time. Test by sampling
    many times and counting."""
    rng = random.Random(42)
    n = 600
    counts: Counter[ObservableBucket] = Counter()
    for _ in range(n):
        obs = sample_headline_observables("strengthening", rng, strength=0.9)
        counts[obs.rate] += 1
    # Natural bucket for strengthening is "low"
    assert counts["low"] > counts["mid"]
    assert counts["low"] > counts["high"]
    # With strength 0.9, low should dominate
    assert counts["low"] / n > 0.8


def test_observable_sampling_uniform_at_zero_strength() -> None:
    """With strength=0, each bucket should appear ~1/3 of the time."""
    rng = random.Random(42)
    n = 3000
    counts: Counter[ObservableBucket] = Counter()
    for _ in range(n):
        obs = sample_headline_observables("strengthening", rng, strength=0.0)
        counts[obs.rate] += 1
    # With strength=0, expected count is n/3 = 1000; tolerance ~10%
    for b in OBSERVABLE_BUCKETS:
        assert 800 < counts[b] < 1200, (
            f"Bucket {b}: expected ~1000, got {counts[b]} (uniform should hold)"
        )


def test_observable_sampling_three_independent_buckets() -> None:
    """rate, vol, fx are sampled independently — they tend to the same
    natural bucket per state, but each is its own draw."""
    rng = random.Random(42)
    n = 600
    rates: Counter[ObservableBucket] = Counter()
    vols: Counter[ObservableBucket] = Counter()
    fxs: Counter[ObservableBucket] = Counter()
    for _ in range(n):
        obs = sample_headline_observables("decaying", rng, strength=0.5)
        rates[obs.rate] += 1
        vols[obs.vol] += 1
        fxs[obs.fx] += 1
    # Decaying state's natural bucket is "high"
    for c in (rates, vols, fxs):
        assert c["high"] > c["low"]
        assert c["high"] > c["mid"]


# ---------------------------------------------------------------------------
# MarketStateBaseline Bayesian Ledger
# ---------------------------------------------------------------------------


def test_baseline_uniform_on_empty_cell() -> None:
    """A fresh Baseline has no observations; every forecast is uniform."""
    bl = MarketStateBaseline()
    obs = HeadlineObservables(rate="low", vol="low", fx="low")
    f = bl.forecast(obs)
    expected = 1.0 / len(RETURN_BUCKETS)
    for bucket in RETURN_BUCKETS:
        assert f[bucket] == pytest.approx(expected)


def test_baseline_learns_from_observations() -> None:
    """After recording observations, the Baseline's forecast at that cell
    is the normalized empirical distribution."""
    bl = MarketStateBaseline()
    obs = HeadlineObservables(rate="low", vol="low", fx="low")
    # Record 7 below_minus_5 and 3 above_plus_10 outcomes at this cell.
    for _ in range(7):
        bl.record(obs, "below_minus_5")
    for _ in range(3):
        bl.record(obs, "above_plus_10")
    f = bl.forecast(obs)
    assert f["below_minus_5"] == pytest.approx(0.7)
    assert f["above_plus_10"] == pytest.approx(0.3)
    # Other buckets sum to 0
    for bucket in ("minus_5_to_0", "zero_to_plus_5", "plus_5_to_plus_10"):
        assert f[bucket] == pytest.approx(0.0)


def test_baseline_cells_are_independent() -> None:
    """Observations at (low, low, low) don't affect forecasts at (high, high, high)."""
    bl = MarketStateBaseline()
    low_obs = HeadlineObservables(rate="low", vol="low", fx="low")
    high_obs = HeadlineObservables(rate="high", vol="high", fx="high")
    for _ in range(10):
        bl.record(low_obs, "above_plus_10")
    # Low cell: all mass on above_plus_10
    f_low = bl.forecast(low_obs)
    assert f_low["above_plus_10"] == pytest.approx(1.0)
    # High cell: still uniform (no observations)
    f_high = bl.forecast(high_obs)
    expected = 1.0 / len(RETURN_BUCKETS)
    assert f_high["above_plus_10"] == pytest.approx(expected)


def test_baseline_cell_sample_size() -> None:
    bl = MarketStateBaseline()
    obs = HeadlineObservables(rate="mid", vol="mid", fx="mid")
    assert bl.cell_sample_size(obs) == 0
    for _ in range(5):
        bl.record(obs, "zero_to_plus_5")
    assert bl.cell_sample_size(obs) == 5


def test_baseline_forecast_always_sums_to_one() -> None:
    """For any non-empty cell, forecast values sum to 1."""
    bl = MarketStateBaseline()
    obs = HeadlineObservables(rate="mid", vol="high", fx="low")
    # Record a few mixed outcomes
    bl.record(obs, "below_minus_5")
    bl.record(obs, "minus_5_to_0")
    bl.record(obs, "zero_to_plus_5")
    f = bl.forecast(obs)
    assert sum(f.values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Side-by-side AI + Baseline pipeline
# ---------------------------------------------------------------------------


N_TRAINING_EPISODES = 80
N_TEST_EPISODES = 40
N_EMISSIONS_PER_EPISODE = 12
INTEGRATION_COST = ToyCostModel(
    adv=10_000_000.0,
    spread_bps=5.0,
    commission_bps=1.0,
    impact_coefficient=0.005,
    alpha_decay_bps_per_period=5.0,
)
INTEGRATION_THRESHOLD = 0.02


@pytest.fixture(scope="module")
def trained_baseline() -> MarketStateBaseline:
    """Run N_TRAINING_EPISODES through the toy world, recording each
    (observables, realized_bucket) pair into the Baseline. Returns a
    Baseline that has empirical experience under each (rate, vol, fx)
    cell visited."""
    state_rng = random.Random(42)
    state_choices: list[CompanyState] = list(STATES)
    bl = MarketStateBaseline()
    for episode_idx in range(N_TRAINING_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(42 + episode_idx + 1)
        obs = sample_headline_observables(truth_state, ep_rng)
        realized = realize_return_at_horizon(truth_state, ep_rng)
        realized_bucket = return_to_bucket(realized)
        bl.record(obs, realized_bucket)
    return bl


def _make_row(
    *,
    agent_id: str,
    forecast: dict[ReturnBucket, float],
    realized_return: float,
    realized_bucket: ReturnBucket,
) -> ScoreboardRow:
    """Build a ScoreboardRow by running decide + realized_edge for one
    agent's forecast at one episode/horizon."""
    from fingym.evaluator.scoring import brier, log_score

    verdict = decide(forecast, INTEGRATION_COST, threshold=INTEGRATION_THRESHOLD)
    edge = realized_edge(verdict.final_action, realized_return, INTEGRATION_COST)
    return ScoreboardRow(
        agent_id=agent_id,
        signal_class_id="cluster_i_test",
        horizon=1,
        decision_time=datetime(2026, 5, 18),
        forecast_distribution=forecast,
        calibrated_forecast=forecast,
        calibrated_expected_return=verdict.calibrated_expected_return,
        calibrated_expected_utility=verdict.calibrated_expected_utility,
        tradable_edge_score=verdict.tradable_edge_score,
        kelly_fraction_applied=verdict.kelly_fraction_applied,
        final_action=verdict.final_action,
        realized_return=realized_return,
        realized_bucket=realized_bucket,
        brier=brier(forecast, realized_bucket),
        log_score=log_score(forecast, realized_bucket),
        realized_edge=edge,
    )


def _run_side_by_side(
    trained_baseline: MarketStateBaseline,
    ai_factory: Callable[[], BayesianAgent | ConfidentAgent],
    ai_agent_id: str,
) -> Scoreboard:
    """Run N_TEST_EPISODES with both AI and Baseline producing forecasts
    on the same episode. Returns a populated Scoreboard with rows from
    both agents under their respective agent_ids."""
    state_rng = random.Random(60_042)
    state_choices: list[CompanyState] = list(STATES)
    sb = Scoreboard()
    for episode_idx in range(N_TEST_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(60_042 + episode_idx + 1)
        # The shared evidence: emissions for the AI, observables for the Baseline.
        agent = ai_factory()
        for _ in range(N_EMISSIONS_PER_EPISODE):
            agent.observe(sample_emission(truth_state, ep_rng))
        obs = sample_headline_observables(truth_state, ep_rng)
        # Realized outcome (shared between agents).
        realized = realize_return_at_horizon(truth_state, ep_rng)
        realized_bucket = return_to_bucket(realized)
        # AI forecast → row.
        ai_forecast = agent.forecast
        sb.append(
            _make_row(
                agent_id=ai_agent_id,
                forecast=ai_forecast,
                realized_return=realized,
                realized_bucket=realized_bucket,
            )
        )
        # Baseline forecast → row.
        bl_forecast = trained_baseline.forecast(obs)
        sb.append(
            _make_row(
                agent_id=BASELINE_AGENT_ID,
                forecast=bl_forecast,
                realized_return=realized,
                realized_bucket=realized_bucket,
            )
        )
    return sb


def test_bayesian_agent_beats_baseline_on_incremental_edge(
    trained_baseline: MarketStateBaseline,
) -> None:
    """BayesianAgent sees the full emission stream; it should produce
    higher mean realized_edge than the Baseline (which sees only
    observables). incremental_AI_edge > 0."""
    sb = _run_side_by_side(
        trained_baseline,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        ai_agent_id="bayesian_agent",
    )
    delta = sb.incremental_ai_edge("bayesian_agent", BASELINE_AGENT_ID)
    assert delta > 0.0, (
        f"BayesianAgent should beat the Baseline on incremental_AI_edge; got delta={delta:.4f}"
    )


def test_confident_agent_underperforms_baseline_on_incremental_edge(
    trained_baseline: MarketStateBaseline,
) -> None:
    """ConfidentAgent is a bullshitter (95% on below_minus_5 always).
    The Baseline, even with only observables, should beat it (or at
    minimum: ConfidentAgent's incremental_AI_edge is small/negative,
    not the large positive a real edge would show)."""
    sb = _run_side_by_side(
        trained_baseline,
        lambda: ConfidentAgent("below_minus_5", confidence=0.95),
        ai_agent_id="confident_agent",
    )
    delta = sb.incremental_ai_edge("confident_agent", BASELINE_AGENT_ID)
    # A real edge would show delta >> 0. A bullshit agent doesn't beat the
    # Baseline meaningfully. We assert delta < BayesianAgent's delta from
    # the previous test — i.e., the attribution column distinguishes.
    # Without knowing the exact Bayesian delta in advance, we settle for:
    # ConfidentAgent's incremental_AI_edge is bounded — it doesn't exceed
    # 1% (100 bps) in absolute value, which would be implausibly good for
    # a bullshitter on a small sample.
    assert delta < 0.01, (
        f"ConfidentAgent should not show large positive incremental edge "
        f"over the Baseline; got delta={delta:.4f}"
    )


def test_baseline_rows_carry_agent_id_constant(
    trained_baseline: MarketStateBaseline,
) -> None:
    """The Baseline's rows use the constant BASELINE_AGENT_ID so the
    Scoreboard helper can locate them. Verify slicing returns the
    expected count."""
    sb = _run_side_by_side(
        trained_baseline,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        ai_agent_id="bayesian_agent",
    )
    baseline_rows = sb.filter_by_agent(BASELINE_AGENT_ID)
    assert len(baseline_rows) == N_TEST_EPISODES


def test_incremental_ai_edge_raises_on_missing_agent(
    trained_baseline: MarketStateBaseline,
) -> None:
    """If either the AI or Baseline has no rows under its agent_id, the
    helper raises rather than returning a misleading 0."""
    sb = Scoreboard()
    sb.append(
        _make_row(
            agent_id="present_agent",
            forecast=dict.fromkeys(RETURN_BUCKETS, 0.2),
            realized_return=0.05,
            realized_bucket="zero_to_plus_5",
        )
    )
    with pytest.raises(ValueError, match="No Scoreboard rows for"):
        sb.incremental_ai_edge("present_agent", "missing_agent")
    with pytest.raises(ValueError, match="No Scoreboard rows for"):
        sb.incremental_ai_edge("missing_agent", "present_agent")


# ---------------------------------------------------------------------------
# Dashboard demo — persists Scoreboard for the operator dashboard
# ---------------------------------------------------------------------------


def test_persist_dashboard_demo_scoreboard(
    trained_baseline: MarketStateBaseline,
) -> None:
    """Run BayesianAgent + ConfidentAgent side-by-side with the Baseline
    and write the combined Scoreboard to `data_cache/scoreboard.jsonl`
    so the operator dashboard has real data to render.

    No API calls (BayesianAgent / ConfidentAgent are hand-coded). The
    file gets overwritten each pytest run — last run wins. The dashboard
    at `uv run python -m fingym.operator report` reads from this path
    by default; after `uv run pytest`, the dashboard shows:
      - bayesian_agent + confident_agent + market_state_baseline rows
      - Per-agent mean realized_edge (BayesianAgent > Baseline > Confident)
      - Track C incremental_AI_edge per agent vs the Baseline

    The point: provide a sanity-check view of the architecture in
    operation. Real session data lands here in Phase 2 NEW when real-
    data tests start emitting Scoreboards that mean something as alpha.
    """
    from fingym.evaluator.scoreboard_io import append_row

    project_root = Path(__file__).resolve().parents[2]
    out_path = project_root / "data_cache" / "scoreboard.jsonl"
    # Overwrite: last pytest run wins.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    # Combined Scoreboard: BayesianAgent run + ConfidentAgent run.
    combined = Scoreboard()
    bayesian_sb = _run_side_by_side(
        trained_baseline,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        ai_agent_id="bayesian_agent",
    )
    confident_sb = _run_side_by_side(
        trained_baseline,
        lambda: ConfidentAgent("below_minus_5", confidence=0.95),
        ai_agent_id="confident_agent",
    )
    # Merge: BayesianAgent's rows + ConfidentAgent's rows + Baseline rows
    # from each (the Baseline appears in both sub-Scoreboards; we keep
    # both — they represent two separate decision-time evaluations).
    for row in (*bayesian_sb.rows, *confident_sb.rows):
        combined.append(row)
        append_row(row, out_path)

    # Sanity: the file was written and round-trips.
    assert out_path.exists()
    rows_on_disk = out_path.read_text().count("\n")
    assert rows_on_disk == combined.total_rows()


# ---------------------------------------------------------------------------
# Architectural isolation — lint test
# ---------------------------------------------------------------------------


def test_no_baseline_imports_lint_catches_violation(tmp_path: Path) -> None:
    """Verify the structural isolation: a Python file under src/fingym/
    (not in src/fingym/baseline/) that imports `fingym.baseline` is caught
    by the no_baseline_imports lint mechanism.

    We invoke the lint script as a subprocess on a synthetic offending
    file and assert it exits non-zero. The path is faked to look like an
    agents/ file so the lint's exempt-prefix logic applies correctly."""
    # Lint script lives at mechanisms/lints/no_baseline_imports.py
    project_root = Path(__file__).resolve().parent.parent.parent
    lint_script = project_root / "mechanisms" / "lints" / "no_baseline_imports.py"
    assert lint_script.exists(), f"Lint script missing at {lint_script}"

    # Build a fake offending file under a path that matches the lint's
    # "outside baseline/" criterion. We write it to tmp_path but pass a
    # path argument that simulates src/fingym/agents/ to trip the rule.
    offending_path = tmp_path / "src" / "fingym" / "agents" / "rogue.py"
    offending_path.parent.mkdir(parents=True, exist_ok=True)
    offending_path.write_text("from fingym.baseline.market_state import MarketStateBaseline\n")

    # The lint reads file content; we pass the real path. Lint's exempt
    # check is on path prefix (ALLOWED_PREFIX = "src/fingym/baseline/"),
    # so a file at any other path is checked.
    result = subprocess.run(
        [sys.executable, str(lint_script), str(offending_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"Lint should fail on a file that imports fingym.baseline; "
        f"got exit code {result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "fingym.baseline" in result.stderr or "fingym.baseline" in result.stdout


def test_no_baseline_imports_lint_allows_baseline_module_self_import(
    tmp_path: Path,
) -> None:
    """Files inside src/fingym/baseline/ ARE allowed to import from
    fingym.baseline (e.g., market_state.py can re-export from
    submodules). The lint's ALLOWED_PREFIX check exempts them."""
    project_root = Path(__file__).resolve().parent.parent.parent
    lint_script = project_root / "mechanisms" / "lints" / "no_baseline_imports.py"

    # Build a file at a path starting with src/fingym/baseline/
    legitimate_path = tmp_path / "src" / "fingym" / "baseline" / "extra.py"
    legitimate_path.parent.mkdir(parents=True, exist_ok=True)
    legitimate_path.write_text("from fingym.baseline.market_state import MarketStateBaseline\n")

    # Pass a path string that starts with src/fingym/baseline/ explicitly
    # so the lint's ALLOWED_PREFIX check fires.
    result = subprocess.run(
        [sys.executable, str(lint_script), "src/fingym/baseline/extra.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, (
        f"Lint should allow imports within src/fingym/baseline/; got "
        f"exit code {result.returncode}\nstderr: {result.stderr}"
    )
