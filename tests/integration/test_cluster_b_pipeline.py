"""Cluster B end-to-end pipeline (PYRAMID Stone 11d-c, BUILD.md Phase 1 NEW Cluster B).

Locks in the Cluster B exit gate: the full Stone 11b → 11c → 11d pipeline
(toy → forecast → Ledger → calibrator.shrink → action_engine.decide)
produces the expected verdict distribution across the three adversarial
agents:

  - ConfidentAgent: raw 0.95-on-below_minus_5 forecast would short hard,
    but post-Stone-11c shrinkage flattens the distribution; the Stone
    11d gate emits NoAction in nearly every episode.
  - UniformAgent: zero discriminating information; emits NoAction in
    every episode under any meaningful threshold.
  - BayesianAgent: forecast varies with evidence; trade rate strictly
    between 0% and 100% across episodes.

Plus one counterfactual test that pins down Stone 11c's role: without
calibration, ConfidentAgent's raw forecast clears the gate and trades
short. With calibration, it does not. Stone 11c is load-bearing.
"""

from __future__ import annotations

import random
from collections.abc import Callable

import pytest

from fingym.action.action_engine import (
    ActionEngineVerdict,
    ToyCostModel,
    decide,
)
from fingym.action.calibrator import shrink
from fingym.agents.contract import NoAction, TradeAction
from fingym.ledger.forecast_ledger import ForecastLedger
from fingym.toys.adversarial_agents import (
    DEFAULT_BAYESIAN_PRIOR,
    Agent,
    BayesianAgent,
    ConfidentAgent,
    UniformAgent,
)
from fingym.toys.synthetic_market import (
    STATES,
    CompanyState,
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
)

CONFIDENT_SCI = "confident_static"
UNIFORM_SCI = "uniform_static"
BAYESIAN_SCI = "bayesian_3state_toy"

INTEGRATION_COST = ToyCostModel(round_trip_cost=0.01)
# Threshold above the +2.3% intrinsic long bias from asymmetric bucket midpoints
# minus 1% cost. Lets the BayesianAgent through on strong-evidence episodes
# while filtering Uniform and post-shrinkage Confident.
INTEGRATION_THRESHOLD = 0.03

N_LEDGER_EPISODES = 100
N_EMISSIONS_PER_EPISODE = 12
N_TEST_EPISODES = 50


@pytest.fixture(scope="module")
def populated_ledger() -> ForecastLedger:
    """Build a Ledger by running 100 episodes through Confident, Uniform,
    and Bayesian agents — same shape as test_forecast_ledger_cluster_a's
    fixture, rebuilt locally for module isolation."""
    state_rng = random.Random(42)
    state_choices: list[CompanyState] = list(STATES)
    ledger = ForecastLedger()

    for episode_idx in range(N_LEDGER_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(42 + episode_idx + 1)
        actors: list[Agent] = [
            ConfidentAgent("below_minus_5", confidence=0.95),
            UniformAgent(),
            BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        ]
        for _ in range(N_EMISSIONS_PER_EPISODE):
            emission = sample_emission(truth_state, ep_rng)
            for a in actors:
                a.observe(emission)
        realized_return = realize_return_at_horizon(truth_state, ep_rng)
        realized_bucket = return_to_bucket(realized_return)
        for a in actors:
            ledger.record(a.signal_class_id, a.forecast, realized_bucket)

    return ledger


def _run_test_episodes(
    populated_ledger: ForecastLedger,
    agent_factory: Callable[[], Agent],
) -> list[ActionEngineVerdict]:
    """Run N_TEST_EPISODES fresh episodes; for each, instantiate a new agent
    via the factory, feed it emissions, then run the full shrink → decide
    pipeline. Returns the list of verdicts."""
    state_rng = random.Random(10_042)
    state_choices: list[CompanyState] = list(STATES)
    verdicts: list[ActionEngineVerdict] = []

    for episode_idx in range(N_TEST_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(10_042 + episode_idx + 1)
        agent = agent_factory()
        for _ in range(N_EMISSIONS_PER_EPISODE):
            agent.observe(sample_emission(truth_state, ep_rng))
        calibrated = shrink(agent.forecast, agent.signal_class_id, populated_ledger)
        verdict = decide(calibrated, INTEGRATION_COST, threshold=INTEGRATION_THRESHOLD)
        verdicts.append(verdict)

    return verdicts


# ---------------------------------------------------------------------------
# Three-agent crush behavior
# ---------------------------------------------------------------------------


def test_confident_agent_nearly_universally_noaction(
    populated_ledger: ForecastLedger,
) -> None:
    """Post-Stone-11c shrinkage crushes ConfidentAgent's 0.95 claim toward
    the empirical 0.27 truth-rate, flattening the forecast. Stone 11d's
    gate then filters it: NoAction in (nearly) every episode."""
    verdicts = _run_test_episodes(
        populated_ledger,
        lambda: ConfidentAgent("below_minus_5", confidence=0.95),
    )
    no_action_count = sum(1 for v in verdicts if isinstance(v.final_action, NoAction))
    assert no_action_count >= 45, (
        f"Expected >= 45/{N_TEST_EPISODES} NoAction for ConfidentAgent "
        f"after shrinkage; got {no_action_count}/{N_TEST_EPISODES}"
    )


def test_uniform_agent_always_noaction(
    populated_ledger: ForecastLedger,
) -> None:
    """UniformAgent has zero discriminating information. Threshold 0.03
    absorbs the +2.3% intrinsic long bias from asymmetric bucket midpoints
    minus 1% cost. Verdict: NoAction in every episode."""
    verdicts = _run_test_episodes(populated_ledger, UniformAgent)
    no_action_count = sum(1 for v in verdicts if isinstance(v.final_action, NoAction))
    assert no_action_count == N_TEST_EPISODES, (
        f"Expected {N_TEST_EPISODES}/{N_TEST_EPISODES} NoAction for UniformAgent; "
        f"got {no_action_count}/{N_TEST_EPISODES}"
    )


def test_bayesian_agent_trades_some_episodes_and_not_others(
    populated_ledger: ForecastLedger,
) -> None:
    """BayesianAgent's forecast varies with the evidence stream. Some
    episodes produce strong, well-calibrated forecasts that survive
    shrinkage and clear the gate; others produce weak forecasts that
    don't. Trade rate strictly between 0% and 100%."""
    verdicts = _run_test_episodes(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
    )
    trade_count = sum(1 for v in verdicts if isinstance(v.final_action, TradeAction))
    no_action_count = sum(1 for v in verdicts if isinstance(v.final_action, NoAction))
    assert trade_count + no_action_count == N_TEST_EPISODES
    assert 0 < trade_count < N_TEST_EPISODES, (
        f"Expected mixed verdicts for BayesianAgent; got {trade_count} trades / "
        f"{no_action_count} NoActions out of {N_TEST_EPISODES}"
    )


# ---------------------------------------------------------------------------
# Counterfactual: Stone 11c is load-bearing
# ---------------------------------------------------------------------------


def test_confident_agent_raw_forecast_would_trade_short() -> None:
    """Counterfactual that proves Stone 11c's role. Feed ConfidentAgent's
    raw forecast directly to the Action Engine, bypassing calibration. The
    raw 0.95-on-below_minus_5 forecast has E[r] = -7.36%; with cost 1% and
    threshold 3%, tradable_edge_score = +3.36% (positive) -> short with
    conviction. With Stone 11c shrinkage in the loop, the same forecast
    is crushed and the engine emits NoAction. Stone 11c is load-bearing,
    not decoration."""
    raw_forecast = ConfidentAgent("below_minus_5", confidence=0.95).forecast
    verdict = decide(raw_forecast, INTEGRATION_COST, threshold=INTEGRATION_THRESHOLD)
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.final_action.direction == "short"
    assert verdict.final_action.expression_type == "equity-short"
    assert verdict.tradable_edge_score > 0


# ---------------------------------------------------------------------------
# Verdict shape check
# ---------------------------------------------------------------------------


def test_verdict_fields_populated_on_sample_pipeline_run(
    populated_ledger: ForecastLedger,
) -> None:
    """One end-to-end pipeline run; verify the five Contract verification
    fields exposed by ActionEngineVerdict are all populated with sensible
    values."""
    agent = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
    ep_rng = random.Random(42)
    for _ in range(N_EMISSIONS_PER_EPISODE):
        agent.observe(sample_emission("strengthening", ep_rng))

    calibrated = shrink(agent.forecast, agent.signal_class_id, populated_ledger)
    verdict = decide(calibrated, INTEGRATION_COST, threshold=INTEGRATION_THRESHOLD)

    assert isinstance(verdict.calibrated_expected_return, float)
    assert isinstance(verdict.calibrated_expected_utility, float)
    assert isinstance(verdict.tradable_edge_score, float)
    assert verdict.kelly_fraction_applied >= 0.0
    assert verdict.final_action is not None
    # Score arithmetic must be consistent.
    assert verdict.tradable_edge_score == pytest.approx(
        verdict.calibrated_expected_utility - INTEGRATION_THRESHOLD, abs=1e-12
    )
