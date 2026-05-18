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

import math
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
    """Structured cost model for the Phase 1 NEW toy MVP (Cluster C, Stone 14).

    Replaces the Cluster-B-era single round-trip constant with the structured
    decomposition from PYRAMID Stone 14:

        round_trip_cost(notional, horizon_periods) =
            spread_bps * 1e-4
          + commission_bps * 1e-4
          + impact_coefficient * sqrt(notional / adv)
          + alpha_decay_bps_per_period * horizon_periods * 1e-4

    Used in two directions, with the same components:
      - Forward (Stone 11d, Action Engine): round_trip_cost_at feeds the
        gate's calibrated_expected_utility.
      - Backward (Stone 14, scoreboard): same method, evaluated against the
        actual TradeAction.notional, feeds realized_edge.

    All fields are non-negative; `adv` must be strictly positive. Validation
    runs at __post_init__.

    `ToyCostModel.flat(round_trip_cost)` builds a size-independent model
    (spread captures the whole round trip; impact and decay are zero) — a
    drop-in replacement for the Cluster-B-era ToyCostModel(round_trip_cost),
    useful in tests and simple scenarios.
    """

    adv: float
    spread_bps: float = 0.0
    commission_bps: float = 0.0
    impact_coefficient: float = 0.0
    alpha_decay_bps_per_period: float = 0.0

    def __post_init__(self) -> None:
        if self.adv <= 0:
            raise ValueError(f"adv must be > 0; got {self.adv}")
        for name, value in (
            ("spread_bps", self.spread_bps),
            ("commission_bps", self.commission_bps),
            ("impact_coefficient", self.impact_coefficient),
            ("alpha_decay_bps_per_period", self.alpha_decay_bps_per_period),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0; got {value}")

    def round_trip_cost_at(self, notional: float, horizon_periods: int = 1) -> float:
        """Total round-trip cost as a fraction of notional at the given size
        and horizon. Combines spread + commission + sqrt-law impact + linear
        alpha decay.
        """
        if notional < 0:
            raise ValueError(f"notional must be >= 0; got {notional}")
        if horizon_periods < 0:
            raise ValueError(f"horizon_periods must be >= 0; got {horizon_periods}")
        spread = self.spread_bps * 1e-4
        commission = self.commission_bps * 1e-4
        impact = self.impact_coefficient * math.sqrt(notional / self.adv)
        decay = self.alpha_decay_bps_per_period * horizon_periods * 1e-4
        return spread + commission + impact + decay

    @classmethod
    def flat(cls, round_trip_cost: float) -> ToyCostModel:
        """Build a size-independent cost model where `spread` carries the
        entire round-trip cost. Drop-in replacement for the Cluster-B-era
        ToyCostModel(round_trip_cost=X); produces the same `round_trip_cost_at`
        value for any notional / horizon.
        """
        if round_trip_cost < 0:
            raise ValueError(f"round_trip_cost must be >= 0; got {round_trip_cost}")
        return cls(
            adv=1.0,
            spread_bps=round_trip_cost * 1e4,
            commission_bps=0.0,
            impact_coefficient=0.0,
            alpha_decay_bps_per_period=0.0,
        )


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
    horizon_periods: int = 1,
) -> ActionEngineVerdict:
    """Decide whether to trade given the calibrated forecast.

    The single signed scalar `tradable_edge_score` is the gate verdict.
    Positive -> TradeAction with fractional-Kelly sizing in the direction of
    sign(expected_return). Non-positive -> NoAction with a reason string.

    Cost is evaluated at the full `notional_base` (conservative upper bound;
    actual deployed notional after fractional-Kelly sizing may be smaller).
    This is the toy MVP's choice — production iterates or binds cost to the
    final trade size.

    Raises ValueError on invalid inputs (negative threshold, kelly_fraction
    outside (0, 1], non-positive notional_base). The cost model validates
    itself at construction.
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

    expected_return = _expected_return(calibrated_forecast)
    variance = _variance(calibrated_forecast, expected_return)

    # Expected utility = profit in the profitable direction, minus structured
    # costs at the conservative notional cap. A bearish forecast (E[r] < 0)
    # is exploitable by going short.
    round_trip_cost = cost_model.round_trip_cost_at(notional_base, horizon_periods)
    calibrated_expected_utility = abs(expected_return) - round_trip_cost
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
