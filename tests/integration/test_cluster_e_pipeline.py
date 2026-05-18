"""Cluster E end-to-end (PYRAMID Stones 24 + 26 in toy mode).

Two mechanisms exercised:

1. Stone 24 — PIT discipline:
   - `time_leak_guard` returns only records with `as_known <= query_tick`.
   - Restatements: latest revision per `as_of` wins under the guard.
   - A Bayesian agent's forecast differs depending on whether a
     restatement is within their query window — concrete proof of PIT.

2. Stone 26 — survivorship + delistings:
   - `realize_returns_at_horizons` honors `delist_at` + `delist_payoff`.
   - Realized edge for a delisted-horizon Contract reflects the delist
     payoff minus structured costs (deeply negative for bankruptcy).
   - Scoreboard preserves delisted rows; mean aggregations include the
     losses (no silent survivorship).

After Cluster E, the architecture is PIT-disciplined and survivorship-
defended at the toy level. Phase 2 NEW substitutes real vendor `as_known`
timestamps and real corporate-action feeds into the same plumbing.
"""

from __future__ import annotations

import random
from datetime import datetime

import pytest

from fingym.action.action_engine import ToyCostModel
from fingym.agents.contract import TradeAction
from fingym.evaluator.realized_edge import realized_edge
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.toys.adversarial_agents import DEFAULT_BAYESIAN_PRIOR, BayesianAgent
from fingym.toys.synthetic_market import (
    EmissionRecord,
    realize_returns_at_horizons,
    return_to_bucket,
    time_leak_guard,
)

# ---------------------------------------------------------------------------
# Stone 24 — PIT discipline + time_leak_guard
# ---------------------------------------------------------------------------


def test_time_leak_guard_filters_future_records() -> None:
    """An agent at query_tick=10 cannot see records published later."""
    records = [
        EmissionRecord(as_of=1, as_known=5, value="strong"),
        EmissionRecord(as_of=2, as_known=8, value="weak"),
        EmissionRecord(as_of=3, as_known=12, value="strong"),  # future
        EmissionRecord(as_of=4, as_known=20, value="mixed"),  # future
    ]
    visible = time_leak_guard(records, query_tick=10)
    assert [r.as_of for r in visible] == [1, 2]
    assert all(r.as_known <= 10 for r in visible)


def test_time_leak_guard_picks_latest_per_as_of_under_restatement() -> None:
    """Same as_of with multiple as_known (revisions): latest wins under query."""
    records = [
        EmissionRecord(as_of=1, as_known=5, value="strong"),  # initial
        EmissionRecord(as_of=1, as_known=15, value="weak"),  # revision
    ]
    # Before revision becomes known: see only initial
    early = time_leak_guard(records, query_tick=10)
    assert len(early) == 1
    assert early[0].value == "strong"
    # After revision becomes known: see revised value
    late = time_leak_guard(records, query_tick=20)
    assert len(late) == 1
    assert late[0].value == "weak"


def test_time_leak_guard_returns_sorted_by_as_of() -> None:
    """Output is deterministic by as_of order."""
    records = [
        EmissionRecord(as_of=5, as_known=1, value="strong"),
        EmissionRecord(as_of=1, as_known=2, value="weak"),
        EmissionRecord(as_of=3, as_known=3, value="mixed"),
    ]
    visible = time_leak_guard(records, query_tick=10)
    assert [r.as_of for r in visible] == [1, 3, 5]


def test_time_leak_guard_empty_under_early_query() -> None:
    """All records are future-as_known: visible list is empty."""
    records = [EmissionRecord(as_of=1, as_known=100, value="strong")]
    assert time_leak_guard(records, query_tick=50) == []


def test_time_leak_guard_handles_multiple_restatements_per_as_of() -> None:
    """Three revisions of the same as_of: latest known wins at each query time."""
    records = [
        EmissionRecord(as_of=1, as_known=5, value="strong"),
        EmissionRecord(as_of=1, as_known=10, value="mixed"),
        EmissionRecord(as_of=1, as_known=15, value="weak"),
    ]
    assert time_leak_guard(records, query_tick=4) == []
    assert time_leak_guard(records, query_tick=7)[0].value == "strong"
    assert time_leak_guard(records, query_tick=12)[0].value == "mixed"
    assert time_leak_guard(records, query_tick=20)[0].value == "weak"


def test_agent_forecast_changes_after_restatement_becomes_visible() -> None:
    """Concrete PIT scenario: a Bayesian agent's forecast differs depending
    on whether a restatement is within their query window. This is the
    structural proof that PIT discipline matters — the same record set
    yields different forecasts at different decision times."""
    records: list[EmissionRecord] = [
        EmissionRecord(as_of=t, as_known=t, value="strong") for t in range(5)
    ]
    # Restatement: at as_known=20, revise the as_of=4 emission to "weak"
    records.append(EmissionRecord(as_of=4, as_known=20, value="weak"))

    # Agent at query_tick=10 (revision not yet known)
    agent_before = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="before")
    for r in time_leak_guard(records, query_tick=10):
        agent_before.observe(r.value)
    forecast_before = dict(agent_before.forecast)

    # Agent at query_tick=25 (revision now known)
    agent_after = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="after")
    for r in time_leak_guard(records, query_tick=25):
        agent_after.observe(r.value)
    forecast_after = dict(agent_after.forecast)

    # Forecasts must differ — one "strong" emission got revised to "weak".
    assert forecast_before != forecast_after


# ---------------------------------------------------------------------------
# Stone 26 — delistings
# ---------------------------------------------------------------------------


def test_delisting_returns_fixed_payoff_at_post_delist_horizons() -> None:
    """Horizons >= delist_at return delist_payoff exactly; earlier horizons
    are drawn from the normal state-conditional distribution."""
    rng = random.Random(42)
    returns = realize_returns_at_horizons(
        "strengthening",
        rng,
        horizons=(3, 6, 12),
        delist_at=5,
        delist_payoff=-0.90,
    )
    # h=3 < delist_at; drawn from N(0.07, 0.04) -- vanishingly small chance == -0.90
    assert returns[3] != -0.90
    # h=6, h=12 >= delist_at; exactly the payoff
    assert returns[6] == -0.90
    assert returns[12] == -0.90


def test_delisting_at_horizon_boundary_is_inclusive() -> None:
    """A horizon exactly equal to delist_at counts as delisted (>=, not >)."""
    rng = random.Random(42)
    returns = realize_returns_at_horizons(
        "strengthening", rng, horizons=(5,), delist_at=5, delist_payoff=-0.50
    )
    assert returns[5] == -0.50


def test_delisting_without_payoff_raises() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError, match="delist_at set without delist_payoff"):
        realize_returns_at_horizons("strengthening", rng, horizons=(3,), delist_at=5)


def test_payoff_without_delist_at_raises() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError, match="delist_payoff set without delist_at"):
        realize_returns_at_horizons("strengthening", rng, horizons=(3,), delist_payoff=-0.5)


def test_no_delist_args_falls_back_to_normal_draws() -> None:
    """Backward compatibility: no delist args -> original (Stone 10) behavior."""
    rng = random.Random(42)
    returns = realize_returns_at_horizons("strengthening", rng, horizons=(1, 3))
    # Independent draws -> generally different
    assert returns[1] != returns[3]
    # Both are plausibly in [-0.20, 0.20] range under N(0.07, 0.04)
    assert -0.20 < returns[1] < 0.20
    assert -0.20 < returns[3] < 0.20


# ---------------------------------------------------------------------------
# Stone 26 — delistings flow through to realized_edge + Scoreboard
# ---------------------------------------------------------------------------


def _structured_cost() -> ToyCostModel:
    return ToyCostModel(
        adv=10_000_000.0,
        spread_bps=5.0,
        commission_bps=1.0,
        impact_coefficient=0.005,
        alpha_decay_bps_per_period=5.0,
    )


def test_delisted_long_trade_realized_edge_reflects_payoff() -> None:
    """A long Contract at a delisted-horizon realizes delist_payoff;
    realized_edge = delist_payoff * (+1) - cost. Deeply negative for a
    bankruptcy outcome."""
    cost = _structured_cost()
    rng = random.Random(0)
    returns = realize_returns_at_horizons(
        "strengthening", rng, horizons=(12,), delist_at=5, delist_payoff=-0.90
    )
    trade = TradeAction(
        expression_type="equity-long",
        underlying="DELISTED_CO",
        direction="long",
        size=100,
        notional=100_000.0,
    )
    edge = realized_edge(trade, returns[12], cost, horizon_periods=12)
    # nominal_payoff = -0.90 * +1 = -0.90; cost ~ 5+1+5sqrt(0.01)+5*12 bps = 71.6 bps
    # realized_edge ~ -0.90 - 0.00716 ~ -0.907
    assert edge < -0.85


def test_delisted_short_trade_realized_edge_reflects_payoff() -> None:
    """The mirror case: shorting into a -90% bankruptcy yields a big positive
    payoff (modulo costs). Verifies direction sign handling under delist."""
    cost = _structured_cost()
    rng = random.Random(0)
    returns = realize_returns_at_horizons(
        "decaying", rng, horizons=(12,), delist_at=5, delist_payoff=-0.90
    )
    short_trade = TradeAction(
        expression_type="equity-short",
        underlying="DELISTED_CO",
        direction="short",
        size=100,
        notional=100_000.0,
    )
    edge = realized_edge(short_trade, returns[12], cost, horizon_periods=12)
    # nominal_payoff = -0.90 * -1 = +0.90; minus cost ~ 71.6 bps ~ +0.893
    assert edge > 0.85


def test_scoreboard_preserves_delisted_rows_no_silent_survivorship() -> None:
    """The Scoreboard must include delisted Contracts. Mean realized_edge
    aggregations include the delisting's losses — they cannot silently vanish.
    Test: 5 normal +5% trades and 1 bankruptcy-trade. Mean must reflect both."""
    cost = ToyCostModel.flat(0.01)
    sb = Scoreboard()
    decision_time = datetime(2026, 5, 18)

    for i in range(5):
        trade = TradeAction(
            expression_type="equity-long",
            underlying=f"NORMAL_{i}",
            direction="long",
            size=10,
            notional=10_000.0,
        )
        realized_r = 0.05
        edge = realized_edge(trade, realized_r, cost)
        sb.append(
            ScoreboardRow(
                agent_id="bayesian",
                signal_class_id="signal_x",
                horizon=12,
                decision_time=decision_time,
                forecast_distribution={},
                calibrated_forecast={},
                calibrated_expected_return=0.05,
                calibrated_expected_utility=0.04,
                tradable_edge_score=0.03,
                kelly_fraction_applied=0.25,
                final_action=trade,
                realized_return=realized_r,
                realized_bucket=return_to_bucket(realized_r),
                brier=0.5,
                log_score=0.7,
                realized_edge=edge,
            )
        )

    # The one delisted long Contract (bankruptcy)
    delist_trade = TradeAction(
        expression_type="equity-long",
        underlying="DELISTED",
        direction="long",
        size=10,
        notional=10_000.0,
    )
    delist_edge = realized_edge(delist_trade, -0.90, cost)
    sb.append(
        ScoreboardRow(
            agent_id="bayesian",
            signal_class_id="signal_x",
            horizon=12,
            decision_time=decision_time,
            forecast_distribution={},
            calibrated_forecast={},
            calibrated_expected_return=0.05,
            calibrated_expected_utility=0.04,
            tradable_edge_score=0.03,
            kelly_fraction_applied=0.25,
            final_action=delist_trade,
            realized_return=-0.90,
            realized_bucket=return_to_bucket(-0.90),
            brier=1.8,
            log_score=4.0,
            realized_edge=delist_edge,
        )
    )

    # All 6 rows preserved
    assert sb.total_rows() == 6
    # Mean realized_edge dragged down by the delisting — survivorship-bias
    # check. 5 rows at ~+4% each, 1 row at ~-91%; mean ~= (5*0.04 + -0.91)/6 ~ -0.118
    mean_edge = sb.mean_realized_edge()
    assert mean_edge < 0.0, (
        f"Survivorship-bias check: mean realized_edge must reflect the "
        f"delisting; got {mean_edge:.4f}"
    )

    # Filter to the delisted underlying — that row exists
    delisted_rows = [
        r
        for r in sb.rows
        if r.final_action.action_type == "trade"
        and isinstance(r.final_action, TradeAction)
        and r.final_action.underlying == "DELISTED"
    ]
    assert len(delisted_rows) == 1
    assert delisted_rows[0].realized_edge < -0.85
