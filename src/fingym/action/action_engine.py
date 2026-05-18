"""action_engine.py - Tradable-Edge Action Engine (Phase 1 NEW Cluster B, Stone 11d).

Sits downstream of `calibrator.shrink`. Consumes `F_AI_calibrated` (the
calibrated forecast over realized-return buckets), a cost model, and a
margin-of-safety threshold; emits a `TradeAction` if the signed scalar
`tradable_edge_score = calibrated_expected_utility - margin_of_safety_threshold`
is positive, else `NoAction` (a typed first-class peer of `TradeAction`).

The raw forecast never multiplies a payoff. Only `F_AI_calibrated` does.
Operator preference enters through the threshold and Kelly fraction only.

Pipeline (PYRAMID Stone 11d):

  1. expected_return under the calibrated distribution
  2. variance under the calibrated distribution
  3. direction = sign(expected_return);
     calibrated_expected_utility = |expected_return| - round_trip_cost
  4. tradable_edge_score = calibrated_expected_utility - threshold
  5. positive -> TradeAction with fractional-Kelly sizing
     non-positive -> NoAction

Public surface:
  - DEFAULT_THRESHOLD, DEFAULT_KELLY_FRACTION, DEFAULT_NOTIONAL_BASE -
    operator-tunable defaults for the toy MVP.
  - ToyCostModel - frozen dataclass; single round-trip cost in the MVP.
    Cluster C extends to per-name liquidity, sqrt-law impact at deployable
    size, and alpha decay over horizon.
  - ActionEngineVerdict - frozen dataclass with the full engine output;
    suitable for populating the verification-side fields on the Contract
    (calibrated_expected_return, calibrated_expected_utility,
    tradable_edge_score, kelly_fraction_applied, final_action).
  - decide(calibrated_forecast, cost_model, threshold, ...) - main entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fingym.agents.contract import ExpressionType, NoAction, TradeAction
from fingym.ledger.forecast_ledger import ForecastOverBuckets
from fingym.toys.synthetic_market import RETURN_BUCKET_MIDPOINTS, RETURN_BUCKETS

DEFAULT_THRESHOLD: float = 0.01
"""Default margin-of-safety threshold (1.0% over expected utility after costs).

Operator-tunable per signal class as the system matures. Absorbs residual
miscalibration that Stone 11c's shrinkage cannot catch, regime change since
the Ledger filled, model risk, and adverse selection on the price action
when the order arrives.
"""

DEFAULT_KELLY_FRACTION: float = 0.25
"""Default fractional Kelly multiplier (quarter Kelly).

Full Kelly maximizes long-run log-wealth but is volatility-pessimal under
estimation error. Fractional Kelly is the engineering compromise; 0.25 is a
conservative starting point. Operator-tunable per signal class.
"""

DEFAULT_NOTIONAL_BASE: float = 100_000.0
"""Notional capital base for sizing in the toy MVP, in arbitrary units.

Real-data version reads available capital from the broker / portfolio state.
"""


@dataclass(frozen=True)
class ToyCostModel:
    """Toy MVP cost model: single round-trip cost as a fraction of notional.

    Phase 1 NEW Cluster C extends this with per-name liquidity, square-root-law
    impact at deployable size (impact ~ sqrt(size / ADV)), and alpha decay
    over horizon. The MVP API matches what Cluster C will need; the difference
    is the internal computation, not the call site.
    """

    round_trip_cost: float


@dataclass(frozen=True)
class ActionEngineVerdict:
    """Output of one `decide` call.

    Suitable for populating the verification-side fields on the Contract:
      - calibrated_expected_return
      - calibrated_expected_utility
      - tradable_edge_score
      - kelly_fraction_applied
      - final_action (TradeAction or NoAction)

    The verdict is what the auditor reads to reconstruct the engine's
    decision. Raw forecast and signal_class_id live on the Contract; the
    verdict does not duplicate them.
    """

    calibrated_expected_return: float
    calibrated_expected_utility: float
    tradable_edge_score: float
    kelly_fraction_applied: float
    final_action: TradeAction | NoAction


def _expected_return(forecast: ForecastOverBuckets) -> float:
    return sum(forecast[b] * RETURN_BUCKET_MIDPOINTS[b] for b in RETURN_BUCKETS)


def _variance(forecast: ForecastOverBuckets, mean: float) -> float:
    return sum(forecast[b] * (RETURN_BUCKET_MIDPOINTS[b] - mean) ** 2 for b in RETURN_BUCKETS)


def decide(
    calibrated_forecast: ForecastOverBuckets,
    cost_model: ToyCostModel,
    threshold: float = DEFAULT_THRESHOLD,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION,
    underlying: str = "TOY",
    notional_base: float = DEFAULT_NOTIONAL_BASE,
) -> ActionEngineVerdict:
    """Decide whether to trade given the calibrated forecast.

    The single signed scalar `tradable_edge_score` is the gate verdict.
    Positive -> TradeAction with fractional-Kelly sizing in the direction of
    sign(expected_return). Non-positive -> NoAction with a reason string.

    Raises ValueError on invalid inputs (negative threshold, kelly_fraction
    outside (0, 1], non-positive notional_base, negative round_trip_cost).
    """
    if threshold < 0:
        raise ValueError(f"threshold must be >= 0; got {threshold}")
    if not 0 < kelly_fraction <= 1:
        raise ValueError(
            f"kelly_fraction must be in (0, 1]; got {kelly_fraction}. "
            "Full Kelly is k=1; conservative quarter Kelly is k=0.25."
        )
    if notional_base <= 0:
        raise ValueError(f"notional_base must be > 0; got {notional_base}")
    if cost_model.round_trip_cost < 0:
        raise ValueError(f"round_trip_cost must be >= 0; got {cost_model.round_trip_cost}")

    expected_return = _expected_return(calibrated_forecast)
    variance = _variance(calibrated_forecast, expected_return)

    # Expected utility = profit in the profitable direction, minus costs.
    # A bearish forecast (E[r] < 0) is exploitable by going short.
    calibrated_expected_utility = abs(expected_return) - cost_model.round_trip_cost
    tradable_edge_score = calibrated_expected_utility - threshold

    if tradable_edge_score <= 0:
        return ActionEngineVerdict(
            calibrated_expected_return=expected_return,
            calibrated_expected_utility=calibrated_expected_utility,
            tradable_edge_score=tradable_edge_score,
            kelly_fraction_applied=0.0,
            final_action=NoAction(
                reason=(
                    f"tradable_edge_score={tradable_edge_score:.6f} <= 0; "
                    f"calibrated_expected_utility={calibrated_expected_utility:.6f}, "
                    f"threshold={threshold:.6f}."
                ),
            ),
        )

    # Trade fires. Direction follows sign of expected return.
    direction: Literal["long", "short"]
    expression_type: ExpressionType
    if expected_return > 0:
        direction = "long"
        expression_type = "equity-long"
    else:
        direction = "short"
        expression_type = "equity-short"

    # Fractional Kelly sizing. Continuous-return Kelly ~ |mu| / variance,
    # multiplied by the operator's fractional Kelly cap and bounded at 1.
    if variance <= 0:
        # Degenerate: no return uncertainty. The forecast is a point mass at
        # one bucket midpoint. Use the operator's k as the allocation.
        f_practical = kelly_fraction
    else:
        full_kelly = abs(expected_return) / variance
        f_practical = min(1.0, kelly_fraction * full_kelly)

    notional = f_practical * notional_base
    # Toy size: derived from the Kelly fraction expressed in basis-of-100.
    # Minimum 1 unit so size > 0 (TradeAction requires gt=0).
    size = max(1, round(f_practical * 100))

    return ActionEngineVerdict(
        calibrated_expected_return=expected_return,
        calibrated_expected_utility=calibrated_expected_utility,
        tradable_edge_score=tradable_edge_score,
        kelly_fraction_applied=f_practical,
        final_action=TradeAction(
            expression_type=expression_type,
            underlying=underlying,
            direction=direction,
            size=size,
            notional=notional,
        ),
    )


__all__ = [
    "DEFAULT_KELLY_FRACTION",
    "DEFAULT_NOTIONAL_BASE",
    "DEFAULT_THRESHOLD",
    "ActionEngineVerdict",
    "ToyCostModel",
    "decide",
]
