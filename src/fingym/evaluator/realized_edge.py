"""realized_edge.py - Capacity-adjusted realized return (PYRAMID Stone 14).

Scoreboard column. Per-Contract, backward-looking: what the trade actually
netted after frictions actually paid at the deployed size. Distinct from
Stone 11d's forward-looking `calibrated_expected_utility`; the pair forms
an agent-level calibration audit.

Formula:

    realized_edge = nominal_payoff - round_trip_cost_at(notional, horizon_periods)
    nominal_payoff = realized_return * direction

where:
  - realized_return is the labelling-function output at horizon (Stone 2;
    v5 RealizedReturnPlan on the Contract).
  - direction is +1 for long, -1 for short.
  - cost components come from the structured `ToyCostModel` (Stone 14;
    same model the Action Engine uses forward-looking).

NoAction Contracts carry `realized_edge = 0` exactly (no trade, no costs,
no payoff). NoAction still gets a scoreboard row with realized_edge = 0
populated — it participates in agent-level aggregations.

Public surface:
  - realized_edge(action, realized_return, cost_model, horizon_periods) - main entry.
"""

from __future__ import annotations

from fingym.action.action_engine import ToyCostModel
from fingym.agents.contract import NoAction, TradeAction


def realized_edge(
    action: TradeAction | NoAction,
    realized_return: float,
    cost_model: ToyCostModel,
    horizon_periods: int = 1,
) -> float:
    """Compute realized_edge for one Contract.

    For TradeAction: `realized_return * direction - cost`, where direction is
    +1 for long, -1 for short, and cost is the structured `round_trip_cost_at`
    evaluated against the action's actual `notional` and the horizon.

    For NoAction: 0.0 exactly (no payoff, no cost). Caller must still record
    this on the scoreboard — NoAction is a typed first-class peer and
    participates in agent-level aggregations.

    Returns a sign-bearing fraction: positive means the trade netted
    profitable after costs; negative means friction-eater or wrong-direction
    trade.
    """
    if isinstance(action, NoAction):
        return 0.0

    if action.direction == "long":
        direction = 1.0
    else:
        direction = -1.0

    nominal_payoff = realized_return * direction
    cost = cost_model.round_trip_cost_at(action.notional, horizon_periods)
    return nominal_payoff - cost


__all__ = ["realized_edge"]
