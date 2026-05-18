"""Cluster F end-to-end (PYRAMID Stone 30 in toy mode).

First model-driven agent: a frontier LLM reads toy emissions as natural
language, self-tags its forecast with a `signal_class_id` it chooses, and
emits a forecast distribution over the five return buckets via tool-call
structured output. The existing calibrator -> Action Engine ->
realized_edge -> Scoreboard machinery is unchanged.

These tests require a real Anthropic API key (`ANTHROPIC_API_KEY` env
var) and make real API calls. They are auto-skipped when the key is
absent (CI without secrets, local devs without keys, etc.).

Scope: 10 episodes per LLM agent. Each episode = 1 API call. With
Haiku 4.5 (~$1/1M input, ~$5/1M output) and ~1k input + 200 output
tokens per call, ~$0.02 per full test run.
"""

from __future__ import annotations

import os
import random

import pytest

from fingym.action.action_engine import ToyCostModel, decide
from fingym.action.calibrator import shrink
from fingym.agents.contract import NoAction, TradeAction
from fingym.evaluator.realized_edge import realized_edge
from fingym.ledger.forecast_ledger import ForecastLedger
from fingym.llm.anthropic import AnthropicClient
from fingym.toys.adversarial_agents import (
    DEFAULT_BAYESIAN_PRIOR,
    Agent,
    BayesianAgent,
    ConfidentAgent,
    UniformAgent,
)
from fingym.toys.llm_agent import LlmAgent
from fingym.toys.synthetic_market import (
    RETURN_BUCKETS,
    STATES,
    CompanyState,
    Emission,
    ReturnBucket,
    realize_returns_at_horizons,
    return_to_bucket,
    sample_emission,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping Cluster F integration tests.",
)

N_LEDGER_EPISODES = 30  # Smaller Ledger; only used to test the full pipeline
N_TEST_EPISODES = 10
N_EMISSIONS_PER_EPISODE = 12
INTEGRATION_COST = ToyCostModel(
    adv=10_000_000.0,
    spread_bps=5.0,
    commission_bps=1.0,
    impact_coefficient=0.005,
    alpha_decay_bps_per_period=5.0,
)
INTEGRATION_THRESHOLD = 0.03


@pytest.fixture(scope="module")
def anthropic_client() -> AnthropicClient:
    return AnthropicClient()


@pytest.fixture(scope="module")
def populated_ledger() -> ForecastLedger:
    """Populate the Ledger using the hand-coded agents (cheap, no API
    calls). The LLM agent in the test pipeline THEN uses this Ledger
    via the calibrator. The Ledger does not need entries under the
    LLM's signal_class_id — the calibrator's empty-ledger path returns
    the raw forecast unchanged, which is the desired Phase 1 NEW
    behavior for a fresh LLM agent."""
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
        realized = realize_returns_at_horizons(truth_state, ep_rng, horizons=(1,))[1]
        realized_bucket = return_to_bucket(realized)
        for a in actors:
            ledger.record(a.signal_class_id, a.forecast, realized_bucket)
    return ledger


def test_llm_agent_smoke_one_call(anthropic_client: AnthropicClient) -> None:
    """Single API call sanity check. Verifies the SDK plumbing,
    tool-call structured output, and ForecastResponse parsing all work.
    Cheapest meaningful test — fires once per run."""
    agent = LlmAgent(anthropic_client)
    smoke_stream: list[Emission] = ["strong", "strong", "mixed", "strong", "weak"]
    for emission in smoke_stream:
        agent.observe(emission)
    forecast = agent.forecast

    assert set(forecast.keys()) == set(RETURN_BUCKETS)
    total = sum(forecast.values())
    assert abs(total - 1.0) < 1e-6, f"Forecast must sum to 1; got {total}"
    assert all(0.0 <= p <= 1.0 for p in forecast.values())

    # Self-applied signal_class_id is captured (model chose its own).
    assert agent.signal_class_id != "llm_unset"
    assert agent.signal_class_id.strip() != ""


def test_llm_agent_runs_full_pipeline_end_to_end(
    anthropic_client: AnthropicClient, populated_ledger: ForecastLedger
) -> None:
    """Run 10 episodes through the full toy -> agent.forecast (LLM call)
    -> calibrator.shrink -> action_engine.decide -> realize_returns ->
    realized_edge pipeline. Verify end-to-end plumbing works under a real
    model in the cognition layer."""
    state_rng = random.Random(50_042)
    state_choices: list[CompanyState] = list(STATES)
    verdicts = []
    realized_edges = []

    for ep_idx in range(N_TEST_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(50_042 + ep_idx + 1)
        agent = LlmAgent(anthropic_client)
        for _ in range(N_EMISSIONS_PER_EPISODE):
            agent.observe(sample_emission(truth_state, ep_rng))
        raw_forecast = agent.forecast
        # Calibration is a no-op when the Ledger has no entries under the
        # LLM's self-applied signal_class_id (empty-ledger pass-through).
        calibrated = shrink(raw_forecast, agent.signal_class_id, populated_ledger)
        verdict = decide(
            calibrated,
            INTEGRATION_COST,
            threshold=INTEGRATION_THRESHOLD,
            horizon_periods=1,
        )
        realized = realize_returns_at_horizons(truth_state, ep_rng, horizons=(1,))[1]
        edge = realized_edge(verdict.final_action, realized, INTEGRATION_COST, horizon_periods=1)
        verdicts.append(verdict)
        realized_edges.append(edge)

    # Plumbing: all 10 episodes completed without exception.
    assert len(verdicts) == N_TEST_EPISODES
    # Each verdict has populated fields.
    for v in verdicts:
        assert isinstance(v.calibrated_expected_return, float)
        assert isinstance(v.calibrated_expected_utility, float)
        assert isinstance(v.tradable_edge_score, float)
        assert v.final_action is not None


def test_llm_agent_forecast_varies_across_episodes(
    anthropic_client: AnthropicClient,
) -> None:
    """The LLM should produce SOMEWHAT different forecasts when the signal
    stream differs. This is a sanity check that the model is responding to
    the input rather than emitting a constant. Tolerance is generous —
    Haiku 4.5 may produce similar forecasts for similar streams; only the
    fully-divergent case (all-strong vs all-weak) must visibly differ."""
    bullish_agent = LlmAgent(anthropic_client)
    bearish_agent = LlmAgent(anthropic_client)
    for _ in range(8):
        bullish_agent.observe("strong")
        bearish_agent.observe("weak")

    f_bull = bullish_agent.forecast
    f_bear = bearish_agent.forecast

    # Both well-formed
    assert abs(sum(f_bull.values()) - 1.0) < 1e-6
    assert abs(sum(f_bear.values()) - 1.0) < 1e-6

    # Bullish forecast should put MORE mass on the positive buckets than
    # the bearish one does, in aggregate.
    positive_buckets: tuple[ReturnBucket, ...] = (
        "zero_to_plus_5",
        "plus_5_to_plus_10",
        "above_plus_10",
    )
    bull_positive_mass = sum(f_bull[b] for b in positive_buckets)
    bear_positive_mass = sum(f_bear[b] for b in positive_buckets)
    assert bull_positive_mass > bear_positive_mass, (
        f"All-STRONG signal stream should yield more positive-bucket mass "
        f"than all-WEAK; got bull={bull_positive_mass:.3f}, "
        f"bear={bear_positive_mass:.3f}"
    )


def test_llm_agent_caches_forecast_until_new_observation(
    anthropic_client: AnthropicClient,
) -> None:
    """Two consecutive `.forecast` accesses without new observations should
    return the same cached value (and not make a second API call). Cache
    invalidates when a new emission arrives."""
    agent = LlmAgent(anthropic_client)
    cache_stream: list[Emission] = ["strong", "mixed", "strong"]
    for emission in cache_stream:
        agent.observe(emission)
    f1 = agent.forecast
    f2 = agent.forecast
    # Same dict reference because the cached value is returned directly.
    assert f1 is f2

    # New observation invalidates the cache.
    agent.observe("weak")
    f3 = agent.forecast
    assert f3 is not f1


def test_llm_agent_no_action_yields_zero_realized_edge(
    anthropic_client: AnthropicClient, populated_ledger: ForecastLedger
) -> None:
    """If the LLM's forecast doesn't clear the gate, NoAction yields
    realized_edge = 0. This pins the Stone 14 contract under the LLM
    cognition layer."""
    agent = LlmAgent(anthropic_client)
    # Feed an evenly-mixed stream; the LLM is unlikely to find strong edge.
    mixed_stream: list[Emission] = ["mixed"] * 6
    for emission in mixed_stream:
        agent.observe(emission)
    raw = agent.forecast
    calibrated = shrink(raw, agent.signal_class_id, populated_ledger)
    verdict = decide(
        calibrated, INTEGRATION_COST, threshold=0.10, horizon_periods=1
    )  # high threshold -> almost certainly NoAction
    if isinstance(verdict.final_action, NoAction):
        edge = realized_edge(verdict.final_action, 0.05, INTEGRATION_COST)
        assert edge == 0.0
    else:
        # Sometimes the LLM finds enough edge to clear even a 10% threshold;
        # in that case verify the plumbing without asserting NoAction.
        assert isinstance(verdict.final_action, TradeAction)
