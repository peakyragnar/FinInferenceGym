"""Cluster C end-to-end pipeline (PYRAMID Stone 14-c, BUILD.md Phase 1 NEW Cluster C).

Extends the Cluster B pipeline with the Stone 14 backward-looking
realized_edge column. The full chain is now:

  toy -> agent.forecast -> calibrator.shrink -> action_engine.decide
       -> realize_return_at_horizon -> realized_edge

Locks in the Cluster C exit gate:

  - BayesianAgent at SMALL deployment size (low notional vs ADV) has
    aggregate mean realized_edge > 0 across its trades — the agent has
    a real edge, and at small size the sqrt-law impact barely touches it.
  - BayesianAgent at LARGE deployment size (high notional vs ADV) has a
    visibly degraded mean realized_edge — the sqrt-law fires. The
    capacity-bucket slice surfaces the size ceiling.
  - ConfidentAgent's near-universal NoActions carry realized_edge = 0
    exactly. UniformAgent's universal NoActions same.
  - Sqrt-law monotonicity holds across deployment sizes (synthetic
    cost-model only test, no random agents).

After 14-c, Cluster C closes. The toy now exercises the full architecture
from emission -> forecast -> Ledger -> calibrator -> action engine ->
realized_edge with structured frictions including the capacity bucket.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from itertools import pairwise

import pytest

from fingym.action.action_engine import ActionEngineVerdict, ToyCostModel, decide
from fingym.action.calibrator import shrink
from fingym.agents.contract import NoAction, TradeAction
from fingym.evaluator.realized_edge import realized_edge
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

# Structured cost model exercising all four components. Used as the
# integration default; per-test overrides for size sweeps.
INTEGRATION_COST = ToyCostModel(
    adv=10_000_000.0,
    spread_bps=5.0,
    commission_bps=1.0,
    impact_coefficient=0.005,  # 50 bps per sqrt(ADV-fraction)
    alpha_decay_bps_per_period=5.0,
)
INTEGRATION_THRESHOLD = 0.03

N_LEDGER_EPISODES = 100
N_EMISSIONS_PER_EPISODE = 12
N_TEST_EPISODES = 100


@pytest.fixture(scope="module")
def populated_ledger() -> ForecastLedger:
    """Build a Ledger by running 100 episodes through all three adversarial
    agents — same shape as Clusters A and B fixtures."""
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


def _run_pipeline(
    populated_ledger: ForecastLedger,
    agent_factory: Callable[[], Agent],
    cost_model: ToyCostModel,
    notional_base: float,
) -> list[tuple[ActionEngineVerdict, float, float]]:
    """Run N_TEST_EPISODES fresh episodes; for each, return
    (verdict, realized_return, realized_edge)."""
    state_rng = random.Random(20_042)
    state_choices: list[CompanyState] = list(STATES)
    rows: list[tuple[ActionEngineVerdict, float, float]] = []

    for episode_idx in range(N_TEST_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(20_042 + episode_idx + 1)
        agent = agent_factory()
        for _ in range(N_EMISSIONS_PER_EPISODE):
            agent.observe(sample_emission(truth_state, ep_rng))
        calibrated = shrink(agent.forecast, agent.signal_class_id, populated_ledger)
        verdict = decide(
            calibrated,
            cost_model,
            threshold=INTEGRATION_THRESHOLD,
            notional_base=notional_base,
        )
        realized = realize_return_at_horizon(truth_state, ep_rng)
        edge = realized_edge(verdict.final_action, realized, cost_model, horizon_periods=1)
        rows.append((verdict, realized, edge))

    return rows


# ---------------------------------------------------------------------------
# BayesianAgent realized_edge at different sizes
# ---------------------------------------------------------------------------


def test_bayesian_realized_edge_positive_at_small_size(
    populated_ledger: ForecastLedger,
) -> None:
    """At small deployment size ($10k vs $10M ADV = 0.1%), sqrt-law impact is
    negligible. BayesianAgent's real edge dominates frictions. Mean
    realized_edge across all its trades should be positive."""
    rows = _run_pipeline(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        cost_model=INTEGRATION_COST,
        notional_base=10_000.0,
    )
    trade_edges = [edge for v, _, edge in rows if isinstance(v.final_action, TradeAction)]
    assert len(trade_edges) > 0, "BayesianAgent should trade at least once at small size"
    mean_edge = sum(trade_edges) / len(trade_edges)
    assert mean_edge > 0, (
        f"Expected positive mean realized_edge for BayesianAgent at small size; "
        f"got {mean_edge:.4f} across {len(trade_edges)} trades"
    )


def test_bayesian_realized_edge_degrades_at_large_size(
    populated_ledger: ForecastLedger,
) -> None:
    """At large deployment size ($10M = full ADV), sqrt-law impact ~50 bps.
    Mean realized_edge across trades should be visibly smaller than at small
    size. The sqrt-law fires — that's Stone 14's capacity slice in action."""
    small_rows = _run_pipeline(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        cost_model=INTEGRATION_COST,
        notional_base=10_000.0,
    )
    large_rows = _run_pipeline(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        cost_model=INTEGRATION_COST,
        notional_base=10_000_000.0,
    )
    small_edges = [edge for v, _, edge in small_rows if isinstance(v.final_action, TradeAction)]
    large_edges = [edge for v, _, edge in large_rows if isinstance(v.final_action, TradeAction)]
    # Both should trade enough to compare. Mean small > mean large by a clear margin.
    small_mean = sum(small_edges) / len(small_edges) if small_edges else 0.0
    large_mean = sum(large_edges) / len(large_edges) if large_edges else 0.0
    # Sqrt-law impact difference: ~50 bps at large size vs ~1.6 bps at small size.
    # Expect a gap of at least 20 bps in mean realized_edge.
    gap = small_mean - large_mean
    assert gap > 0.002, (
        f"Expected mean realized_edge gap > 20 bps between small and large size "
        f"(sqrt-law signature). Got small={small_mean:.4f}, large={large_mean:.4f}, "
        f"gap={gap:.4f}"
    )


# ---------------------------------------------------------------------------
# NoAction yields realized_edge = 0
# ---------------------------------------------------------------------------


def test_confident_no_actions_yield_zero_realized_edge(
    populated_ledger: ForecastLedger,
) -> None:
    """Every NoAction Contract from ConfidentAgent should carry exactly
    realized_edge = 0 — no trade, no costs, no payoff."""
    rows = _run_pipeline(
        populated_ledger,
        lambda: ConfidentAgent("below_minus_5", confidence=0.95),
        cost_model=INTEGRATION_COST,
        notional_base=100_000.0,
    )
    no_action_edges = [edge for v, _, edge in rows if isinstance(v.final_action, NoAction)]
    assert len(no_action_edges) >= 90, (
        f"Expected near-universal NoAction for ConfidentAgent; got {len(no_action_edges)}"
    )
    assert all(e == 0.0 for e in no_action_edges), (
        "Every NoAction must carry realized_edge = 0.0 exactly"
    )


def test_uniform_no_actions_yield_zero_realized_edge(
    populated_ledger: ForecastLedger,
) -> None:
    """UniformAgent's universal NoActions must all carry realized_edge = 0."""
    rows = _run_pipeline(
        populated_ledger,
        UniformAgent,
        cost_model=INTEGRATION_COST,
        notional_base=100_000.0,
    )
    no_action_edges = [edge for v, _, edge in rows if isinstance(v.final_action, NoAction)]
    assert len(no_action_edges) == N_TEST_EPISODES
    assert all(e == 0.0 for e in no_action_edges)


# ---------------------------------------------------------------------------
# Sqrt-law monotonicity (synthetic, no random agents)
# ---------------------------------------------------------------------------


def test_sqrt_law_monotone_across_deployment_sizes() -> None:
    """Pure cost-model test: for a fixed realized_return and direction,
    realized_edge is strictly monotone decreasing in deployment size across
    the sqrt-law region. No random sampling — deterministic."""
    trade_template = TradeAction(
        expression_type="equity-long",
        underlying="TOY",
        direction="long",
        size=100,
        notional=1.0,  # placeholder; we'll vary
    )
    realized = 0.05  # +5% return
    notionals = [1_000.0, 10_000.0, 100_000.0, 1_000_000.0, 10_000_000.0]
    edges = []
    for n in notionals:
        trade = TradeAction(
            expression_type=trade_template.expression_type,
            underlying=trade_template.underlying,
            direction=trade_template.direction,
            size=trade_template.size,
            notional=n,
        )
        edges.append(realized_edge(trade, realized, INTEGRATION_COST, horizon_periods=1))

    # Monotone decreasing across deployment sizes.
    for a, b in pairwise(edges):
        assert a > b, f"Sqrt-law violation: realized_edge non-monotone across sizes. Got {edges}"
    # The spread between smallest and largest should reflect the sqrt-law
    # impact (~50 bps additional at full ADV vs negligible at 0.01% ADV).
    assert edges[0] - edges[-1] > 0.004, (
        f"Sqrt-law spread too small: {edges[0] - edges[-1]:.4f}; expected > 40 bps"
    )
