"""Cluster D end-to-end pipeline (PYRAMID Stone 10 in code).

Extends the Cluster A/B/C pipeline with multi-horizon scoring. For each
test episode the agent emits a single forecast; that forecast is
independently scored at multiple toy-tick horizons (1, 3, 6, 12). Each
horizon produces its own ScoreboardRow with horizon-specific:
  - round_trip_cost via alpha decay (5 bps per tick accumulates)
  - final_action (may shift Trade → NoAction at long horizon)
  - realized_return (independent draw per horizon from
    realize_returns_at_horizons)
  - realized_edge, brier, log_score

Locks the Stone 10 exit gate (code-level): the Scoreboard correctly
indexes rows by horizon; the same forecast yields monotonically
decreasing calibrated_expected_utility as horizon grows (alpha-decay
signature, per-episode and deterministic); BayesianAgent's mean
realized_edge across consistently-trading episodes declines with
horizon; ConfidentAgent + UniformAgent NoActions carry
realized_edge = 0 at every horizon.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise

import pytest

from fingym.action.action_engine import ActionEngineVerdict, ToyCostModel, decide
from fingym.action.calibrator import shrink
from fingym.agents.contract import NoAction, TradeAction
from fingym.evaluator.realized_edge import realized_edge
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.evaluator.scoring import brier, log_score
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
    realize_returns_at_horizons,
    return_to_bucket,
    sample_emission,
)

HORIZONS: tuple[int, ...] = (1, 3, 6, 12)
INTEGRATION_COST = ToyCostModel(
    adv=10_000_000.0,
    spread_bps=5.0,
    commission_bps=1.0,
    impact_coefficient=0.005,
    alpha_decay_bps_per_period=5.0,
)
INTEGRATION_THRESHOLD = 0.03
NOTIONAL_BASE = 100_000.0
N_LEDGER_EPISODES = 100
N_TEST_EPISODES = 50
N_EMISSIONS_PER_EPISODE = 12


@dataclass(frozen=True)
class EpisodeResult:
    """All scored data from one test episode, indexed by horizon."""

    agent_id: str
    signal_class_id: str
    decision_time: datetime
    verdicts: dict[int, ActionEngineVerdict]
    realized_returns: dict[int, float]
    realized_edges: dict[int, float]
    briers: dict[int, float]
    log_scores: dict[int, float]


@pytest.fixture(scope="module")
def populated_ledger() -> ForecastLedger:
    """Cluster A populated Ledger (100 episodes; single-horizon)."""
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


def _run_test_episodes(
    populated_ledger: ForecastLedger,
    agent_factory: Callable[[], Agent],
    agent_id: str,
) -> list[EpisodeResult]:
    """Run N_TEST_EPISODES; for each, score the agent's forecast at every
    horizon. Returns per-episode results indexed by horizon."""
    state_rng = random.Random(40_042)
    state_choices: list[CompanyState] = list(STATES)
    base_time = datetime(2026, 5, 18)
    results: list[EpisodeResult] = []

    for ep_idx in range(N_TEST_EPISODES):
        truth_state = state_rng.choice(state_choices)
        ep_rng = random.Random(40_042 + ep_idx + 1)
        agent = agent_factory()
        for _ in range(N_EMISSIONS_PER_EPISODE):
            agent.observe(sample_emission(truth_state, ep_rng))
        raw = agent.forecast
        calibrated = shrink(raw, agent.signal_class_id, populated_ledger)
        realized_returns = realize_returns_at_horizons(truth_state, ep_rng, HORIZONS)

        verdicts: dict[int, ActionEngineVerdict] = {}
        edges: dict[int, float] = {}
        briers: dict[int, float] = {}
        log_scores: dict[int, float] = {}
        for h in HORIZONS:
            verdict = decide(
                calibrated,
                INTEGRATION_COST,
                threshold=INTEGRATION_THRESHOLD,
                notional_base=NOTIONAL_BASE,
                horizon_periods=h,
            )
            verdicts[h] = verdict
            realized_r = realized_returns[h]
            realized_b = return_to_bucket(realized_r)
            edges[h] = realized_edge(
                verdict.final_action, realized_r, INTEGRATION_COST, horizon_periods=h
            )
            briers[h] = brier(calibrated, realized_b)
            log_scores[h] = log_score(calibrated, realized_b)

        results.append(
            EpisodeResult(
                agent_id=agent_id,
                signal_class_id=agent.signal_class_id,
                decision_time=base_time + timedelta(days=ep_idx),
                verdicts=verdicts,
                realized_returns=realized_returns,
                realized_edges=edges,
                briers=briers,
                log_scores=log_scores,
            )
        )
    return results


def _build_scoreboard(
    episodes: list[EpisodeResult],
    raw_forecast_for_each: list[dict[str, float] | None] | None = None,
) -> Scoreboard:
    """Flatten per-episode results into a Scoreboard. One row per
    (episode, horizon)."""
    sb = Scoreboard()
    for ep in episodes:
        for h in HORIZONS:
            v = ep.verdicts[h]
            sb.append(
                ScoreboardRow(
                    agent_id=ep.agent_id,
                    signal_class_id=ep.signal_class_id,
                    horizon=h,
                    decision_time=ep.decision_time,
                    forecast_distribution={},  # not tracked per-episode; PYRAMID-stone-19 work
                    calibrated_forecast={},
                    calibrated_expected_return=v.calibrated_expected_return,
                    calibrated_expected_utility=v.calibrated_expected_utility,
                    tradable_edge_score=v.tradable_edge_score,
                    kelly_fraction_applied=v.kelly_fraction_applied,
                    final_action=v.final_action,
                    realized_return=ep.realized_returns[h],
                    realized_bucket=return_to_bucket(ep.realized_returns[h]),
                    brier=ep.briers[h],
                    log_score=ep.log_scores[h],
                    realized_edge=ep.realized_edges[h],
                )
            )
    return sb


# ---------------------------------------------------------------------------
# Scoreboard shape: per-horizon indexing
# ---------------------------------------------------------------------------


def test_scoreboard_indexes_rows_by_horizon(populated_ledger: ForecastLedger) -> None:
    episodes = _run_test_episodes(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        "bayesian",
    )
    sb = _build_scoreboard(episodes)
    assert sb.total_rows() == N_TEST_EPISODES * len(HORIZONS)
    assert set(sb.horizons_seen()) == set(HORIZONS)
    for h in HORIZONS:
        assert len(sb.filter_by_horizon(h)) == N_TEST_EPISODES


# ---------------------------------------------------------------------------
# Per-episode: same forecast, alpha decay shrinks utility monotonically
# ---------------------------------------------------------------------------


def test_calibrated_expected_utility_strictly_decreases_with_horizon(
    populated_ledger: ForecastLedger,
) -> None:
    """For ANY agent on ANY episode, the forecast is the same across
    horizons; only the round-trip cost changes (alpha decay accumulates).
    So calibrated_expected_utility must be strictly decreasing in horizon
    on every single episode. This is the deterministic alpha-decay
    signature — no aggregation, no noise."""
    for agent_factory, agent_id in (
        (lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"), "bayesian"),
        (lambda: ConfidentAgent("below_minus_5", confidence=0.95), "confident"),
        (UniformAgent, "uniform"),
    ):
        episodes = _run_test_episodes(populated_ledger, agent_factory, agent_id)
        for ep in episodes:
            utilities = [ep.verdicts[h].calibrated_expected_utility for h in HORIZONS]
            for u_short, u_long in pairwise(utilities):
                assert u_short > u_long, (
                    f"Agent {agent_id}: calibrated_expected_utility not monotone "
                    f"decreasing in horizon for one episode: {utilities}"
                )


def test_calibrated_expected_return_is_horizon_invariant(
    populated_ledger: ForecastLedger,
) -> None:
    """The forecast doesn't change with horizon; calibrated_expected_return
    is the same across all horizons. This locks the invariant that horizon
    affects the cost side only, not the forecast side."""
    episodes = _run_test_episodes(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        "bayesian",
    )
    for ep in episodes:
        returns = [ep.verdicts[h].calibrated_expected_return for h in HORIZONS]
        assert all(r == returns[0] for r in returns)


# ---------------------------------------------------------------------------
# Bayesian realized_edge degrades with horizon (consistently-trading subset)
# ---------------------------------------------------------------------------


def test_bayesian_realized_edge_degrades_across_horizons_on_intersection(
    populated_ledger: ForecastLedger,
) -> None:
    """On the SUBSET of episodes where BayesianAgent trades at all four
    horizons, mean realized_edge at the shortest horizon is greater than
    at the longest. Filtering to the intersection eliminates selection
    bias from the gate filtering out weaker forecasts at long horizon."""
    episodes = _run_test_episodes(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        "bayesian",
    )
    consistently_trading = [
        ep
        for ep in episodes
        if all(isinstance(ep.verdicts[h].final_action, TradeAction) for h in HORIZONS)
    ]
    assert len(consistently_trading) >= 5, (
        f"Need >= 5 episodes where Bayesian trades at all horizons; got {len(consistently_trading)}"
    )
    sb = _build_scoreboard(consistently_trading)
    short_h, long_h = min(HORIZONS), max(HORIZONS)
    short_mean = sb.mean_realized_edge(sb.filter_by_horizon(short_h))
    long_mean = sb.mean_realized_edge(sb.filter_by_horizon(long_h))
    # The cost difference between h=1 and h=12 is 11 * 5 bps = 55 bps from
    # alpha decay alone. Mean realized_edge difference should reflect that
    # — modulo independent realized_return noise across horizons.
    assert short_mean > long_mean, (
        f"Expected mean realized_edge at h={short_h} > h={long_h} for Bayesian "
        f"trades; got short={short_mean:.4f}, long={long_mean:.4f}"
    )


# ---------------------------------------------------------------------------
# NoAction = 0 at every horizon
# ---------------------------------------------------------------------------


def test_confident_no_actions_yield_zero_edge_at_every_horizon(
    populated_ledger: ForecastLedger,
) -> None:
    episodes = _run_test_episodes(
        populated_ledger,
        lambda: ConfidentAgent("below_minus_5", confidence=0.95),
        "confident",
    )
    for h in HORIZONS:
        no_action_edges = [
            ep.realized_edges[h]
            for ep in episodes
            if isinstance(ep.verdicts[h].final_action, NoAction)
        ]
        # Stone 11d should crush ConfidentAgent on nearly every episode.
        assert len(no_action_edges) >= 45
        assert all(e == 0.0 for e in no_action_edges)


def test_uniform_no_actions_yield_zero_edge_at_every_horizon(
    populated_ledger: ForecastLedger,
) -> None:
    episodes = _run_test_episodes(populated_ledger, UniformAgent, "uniform")
    for h in HORIZONS:
        no_action_edges = [
            ep.realized_edges[h]
            for ep in episodes
            if isinstance(ep.verdicts[h].final_action, NoAction)
        ]
        assert len(no_action_edges) == N_TEST_EPISODES
        assert all(e == 0.0 for e in no_action_edges)


# ---------------------------------------------------------------------------
# Brier / log_score populated per horizon
# ---------------------------------------------------------------------------


def test_brier_and_log_score_populated_per_horizon(
    populated_ledger: ForecastLedger,
) -> None:
    """Brier in [0, 2] for a sum-to-1 distribution; log_score in [0, inf).
    All four horizons get scored independently — different realized buckets
    give different brier/log_score values across horizons in general. The
    Scoreboard aggregation helpers (mean_brier / mean_log_score) produce
    finite per-horizon means."""
    episodes = _run_test_episodes(
        populated_ledger,
        lambda: BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent"),
        "bayesian",
    )
    sb = _build_scoreboard(episodes)
    for h in HORIZONS:
        rows = sb.filter_by_horizon(h)
        assert all(0.0 <= r.brier <= 2.0 for r in rows)
        assert all(r.log_score >= 0.0 for r in rows)
        m_brier = sb.mean_brier(rows)
        m_log = sb.mean_log_score(rows)
        assert 0.0 <= m_brier <= 2.0
        assert m_log >= 0.0


def test_scoreboard_empty_mean_raises() -> None:
    """Calling any mean_* aggregation over an empty row set raises — the
    caller must check for empty first. This pins the API surface."""
    sb = Scoreboard()
    with pytest.raises(ValueError, match="empty"):
        sb.mean_brier()
    with pytest.raises(ValueError, match="empty"):
        sb.mean_log_score()
    with pytest.raises(ValueError, match="empty"):
        sb.mean_realized_edge()
