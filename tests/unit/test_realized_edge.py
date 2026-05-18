"""Unit tests for realized_edge (Stone 14 scoreboard column).

Covers:
  - NoAction returns 0.0 exactly.
  - TradeAction in both directions: long profits on positive realized return,
    short profits on negative realized return.
  - Cost subtraction: realized_edge = nominal_payoff - round_trip_cost.
  - Sqrt-law impact: realized_edge degrades with notional under the
    structured cost model.
  - Alpha-decay: realized_edge degrades with horizon_periods.
  - Hand-computed value matches.
"""

from __future__ import annotations

import pytest

from fingym.action.action_engine import ToyCostModel
from fingym.agents.contract import NoAction, TradeAction
from fingym.evaluator.realized_edge import realized_edge


def _trade(direction: str, notional: float = 100_000.0, size: int = 100) -> TradeAction:
    return TradeAction(
        expression_type="equity-long" if direction == "long" else "equity-short",
        underlying="TOY",
        direction="long" if direction == "long" else "short",
        size=size,
        notional=notional,
    )


# ---------------------------------------------------------------------------
# NoAction path
# ---------------------------------------------------------------------------


def test_no_action_yields_zero_realized_edge() -> None:
    """NoAction Contracts carry realized_edge = 0 exactly. No trade,
    no costs, no payoff."""
    action = NoAction(reason="threshold not cleared")
    cost = ToyCostModel.flat(0.10)  # arbitrary; should be ignored for NoAction
    edge = realized_edge(action, realized_return=0.05, cost_model=cost)
    assert edge == 0.0


def test_no_action_zero_under_zero_realized_return() -> None:
    action = NoAction(reason="anything")
    cost = ToyCostModel.flat(0.0)
    edge = realized_edge(action, realized_return=0.0, cost_model=cost)
    assert edge == 0.0


# ---------------------------------------------------------------------------
# TradeAction direction sign
# ---------------------------------------------------------------------------


def test_long_trade_on_positive_return_yields_positive_edge() -> None:
    trade = _trade("long")
    edge = realized_edge(trade, realized_return=0.05, cost_model=ToyCostModel.flat(0.0))
    assert edge == pytest.approx(0.05)


def test_long_trade_on_negative_return_yields_negative_edge() -> None:
    trade = _trade("long")
    edge = realized_edge(trade, realized_return=-0.03, cost_model=ToyCostModel.flat(0.0))
    assert edge == pytest.approx(-0.03)


def test_short_trade_on_negative_return_yields_positive_edge() -> None:
    """Short profits on negative realized returns."""
    trade = _trade("short")
    edge = realized_edge(trade, realized_return=-0.05, cost_model=ToyCostModel.flat(0.0))
    assert edge == pytest.approx(0.05)


def test_short_trade_on_positive_return_yields_negative_edge() -> None:
    """Short loses on positive realized returns."""
    trade = _trade("short")
    edge = realized_edge(trade, realized_return=0.03, cost_model=ToyCostModel.flat(0.0))
    assert edge == pytest.approx(-0.03)


# ---------------------------------------------------------------------------
# Cost subtraction
# ---------------------------------------------------------------------------


def test_flat_cost_is_subtracted_from_payoff() -> None:
    """Under a flat cost model, realized_edge = realized_return * direction - cost."""
    trade = _trade("long")
    edge = realized_edge(trade, realized_return=0.05, cost_model=ToyCostModel.flat(0.01))
    assert edge == pytest.approx(0.04)


def test_negative_payoff_minus_cost_compounds() -> None:
    """Losing trade plus costs makes edge more negative."""
    trade = _trade("long")
    edge = realized_edge(trade, realized_return=-0.02, cost_model=ToyCostModel.flat(0.01))
    assert edge == pytest.approx(-0.03)


# ---------------------------------------------------------------------------
# Structured cost: sqrt-law impact
# ---------------------------------------------------------------------------


def test_sqrt_law_impact_grows_with_notional() -> None:
    """Larger notional under the structured cost yields larger impact, hence
    smaller realized_edge. impact = impact_coefficient * sqrt(notional/adv)."""
    cost = ToyCostModel(
        adv=1_000_000.0,
        spread_bps=0.0,
        commission_bps=0.0,
        impact_coefficient=0.005,
        alpha_decay_bps_per_period=0.0,
    )
    small_trade = _trade("long", notional=10_000.0)  # 1% of ADV
    big_trade = _trade("long", notional=100_000.0)  # 10% of ADV
    small_edge = realized_edge(small_trade, realized_return=0.03, cost_model=cost)
    big_edge = realized_edge(big_trade, realized_return=0.03, cost_model=cost)
    # Both should be positive; small trade keeps more edge.
    assert small_edge > big_edge
    # Hand-computed: small impact = 0.005 * sqrt(0.01) = 0.0005, big = 0.005 * sqrt(0.10) = 0.00158
    assert small_edge == pytest.approx(0.03 - 0.0005, abs=1e-6)
    assert big_edge == pytest.approx(0.03 - 0.005 * (0.1**0.5), abs=1e-6)


def test_sqrt_law_impact_at_full_adv() -> None:
    """At notional = ADV, impact = impact_coefficient * sqrt(1) = impact_coefficient."""
    cost = ToyCostModel(
        adv=100_000.0,
        spread_bps=0.0,
        commission_bps=0.0,
        impact_coefficient=0.005,
        alpha_decay_bps_per_period=0.0,
    )
    trade = _trade("long", notional=100_000.0)
    edge = realized_edge(trade, realized_return=0.05, cost_model=cost)
    # Impact = 50 bps = 0.005; edge = 0.05 - 0.005 = 0.045
    assert edge == pytest.approx(0.045)


# ---------------------------------------------------------------------------
# Structured cost: alpha decay
# ---------------------------------------------------------------------------


def test_alpha_decay_grows_with_horizon() -> None:
    """Longer horizon under the structured cost yields larger alpha decay."""
    cost = ToyCostModel(
        adv=1_000_000.0,
        spread_bps=0.0,
        commission_bps=0.0,
        impact_coefficient=0.0,  # disable impact via zero coefficient
        alpha_decay_bps_per_period=10.0,  # 10 bps per period
    )
    trade = _trade("long", notional=100_000.0)
    one_period_edge = realized_edge(trade, realized_return=0.05, cost_model=cost, horizon_periods=1)
    six_period_edge = realized_edge(trade, realized_return=0.05, cost_model=cost, horizon_periods=6)
    # Decay 10 bps/period -> 1p costs 0.001, 6p costs 0.006
    assert one_period_edge == pytest.approx(0.049)
    assert six_period_edge == pytest.approx(0.044)
    assert one_period_edge > six_period_edge


# ---------------------------------------------------------------------------
# All components combined: hand-computed
# ---------------------------------------------------------------------------


def test_full_decomposition_matches_hand_computed() -> None:
    """Build a structured cost with all four components and verify the
    realized_edge matches the hand-computed value."""
    cost = ToyCostModel(
        adv=10_000_000.0,
        spread_bps=5.0,
        commission_bps=1.0,
        impact_coefficient=0.005,
        alpha_decay_bps_per_period=2.0,
    )
    trade = _trade("long", notional=100_000.0)  # 1% of ADV
    # Spread = 5 bps = 0.0005
    # Commission = 1 bp = 0.0001
    # Impact = 0.005 * sqrt(0.01) = 0.005 * 0.1 = 0.0005
    # Alpha decay (3 periods) = 2 bps * 3 = 6 bps = 0.0006
    # Total cost = 0.0017
    # Realized return = +0.03; payoff = 0.03; edge = 0.03 - 0.0017 = 0.0283
    edge = realized_edge(trade, realized_return=0.03, cost_model=cost, horizon_periods=3)
    expected = 0.03 - (0.0005 + 0.0001 + 0.0005 + 0.0006)
    assert edge == pytest.approx(expected, abs=1e-9)
