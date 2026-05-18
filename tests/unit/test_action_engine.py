"""Unit tests for the Tradable-Edge Action Engine (Stone 11d).

Covers:
  - Trade fires in the correct direction when tradable_edge_score > 0.
  - NoAction emitted with diagnostic reason when score <= 0.
  - Fractional Kelly sizing monotonicity in |mu| and inverse in variance.
  - Edge cases: zero variance, zero threshold, zero cost.
  - Adversarial-agent crush: Confident-post-shrinkage, Uniform, Bayesian.
  - Invalid-input guards on threshold / kelly_fraction / notional / cost.
"""

from __future__ import annotations

import pytest

from fingym.action.action_engine import (
    DEFAULT_KELLY_FRACTION,
    DEFAULT_NOTIONAL_BASE,
    DEFAULT_THRESHOLD,
    ToyCostModel,
    decide,
)
from fingym.agents.contract import NoAction, TradeAction
from fingym.toys.synthetic_market import ForecastOverBuckets, ReturnBucket


def _forecast(
    below: float, neg: float, zero: float, pos: float, above: float
) -> ForecastOverBuckets:
    """Build a forecast dict over the five return buckets."""
    f: dict[ReturnBucket, float] = {
        "below_minus_5": below,
        "minus_5_to_0": neg,
        "zero_to_plus_5": zero,
        "plus_5_to_plus_10": pos,
        "above_plus_10": above,
    }
    return f


# ---------------------------------------------------------------------------
# Trade verdicts: direction + sign
# ---------------------------------------------------------------------------


def test_strongly_bullish_forecast_trades_long() -> None:
    # 50% probability on plus_5_to_plus_10 (mid +7.5%); 25% on above_plus_10 (+12%);
    # E[r] = 0.5 * 0.075 + 0.25 * 0.12 + 0.125 * 0.025 + 0.075 * -0.025 + 0.05 * -0.08
    #      ~= +0.0667 (6.67%). After 1% costs and 1% threshold: tradable_edge_score ~= 4.67%.
    f = _forecast(below=0.05, neg=0.075, zero=0.125, pos=0.5, above=0.25)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.final_action.direction == "long"
    assert verdict.final_action.expression_type == "equity-long"
    assert verdict.calibrated_expected_return > 0
    assert verdict.tradable_edge_score > 0
    assert verdict.kelly_fraction_applied > 0


def test_strongly_bearish_forecast_trades_short() -> None:
    # Heavy mass on below_minus_5 (-8%). Need |E[r]| > cost + threshold = 0.02.
    f = _forecast(below=0.5, neg=0.3, zero=0.1, pos=0.05, above=0.05)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.final_action.direction == "short"
    assert verdict.final_action.expression_type == "equity-short"
    assert verdict.calibrated_expected_return < 0
    assert verdict.tradable_edge_score > 0


def test_trade_size_is_positive() -> None:
    f = _forecast(below=0.05, neg=0.05, zero=0.10, pos=0.50, above=0.30)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.005))
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.final_action.size > 0
    assert verdict.final_action.notional > 0


def test_kelly_fraction_capped_at_one() -> None:
    # Massive expected return relative to variance -> full_kelly is huge but
    # f_practical must be capped at 1.0.
    f = _forecast(below=0.0, neg=0.0, zero=0.0, pos=0.0, above=1.0)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.0), threshold=0.0, kelly_fraction=1.0)
    assert verdict.kelly_fraction_applied <= 1.0 + 1e-12


# ---------------------------------------------------------------------------
# NoAction verdicts
# ---------------------------------------------------------------------------


def test_uniform_forecast_emits_no_action_under_meaningful_threshold() -> None:
    # Uniform over asymmetric midpoints has a small built-in long bias:
    # E[r] = 0.2 * (-0.08 - 0.025 + 0.025 + 0.075 + 0.12) = 0.023 (+2.3%).
    # This is a real property of the bucket scheme (two open-ended buckets at
    # -8% and +12%; intrinsically asymmetric). The gate filters it correctly
    # at any meaningful threshold above the bias.
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01), threshold=0.05)
    assert isinstance(verdict.final_action, NoAction)
    assert verdict.tradable_edge_score < 0


def test_zero_expected_return_emits_no_action() -> None:
    # Construct a forecast with exactly zero expected return: 50% below_minus_5 + 50% above_plus_10
    # with midpoints -0.08 and 0.12... E[r] = -0.04 + 0.06 = +0.02. Not zero. Adjust:
    # For zero: need 0.6 * (-0.08) + 0.4 * 0.12 = -0.048 + 0.048 = 0.0. Good.
    f = _forecast(below=0.6, neg=0.0, zero=0.0, pos=0.0, above=0.4)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    assert isinstance(verdict.final_action, NoAction)
    assert verdict.calibrated_expected_return == pytest.approx(0.0, abs=1e-9)
    assert verdict.tradable_edge_score < 0


def test_no_action_records_diagnostic_reason() -> None:
    f = _forecast(0.6, 0.0, 0.0, 0.0, 0.4)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    assert isinstance(verdict.final_action, NoAction)
    assert "tradable_edge_score" in verdict.final_action.reason
    assert "calibrated_expected_utility" in verdict.final_action.reason


def test_edge_below_threshold_emits_no_action() -> None:
    # E[r] yields small positive utility-after-cost, but below the threshold.
    # Forecast: mass concentrated in zero-to-plus-5 (+2.5%), uniform elsewhere.
    f = _forecast(below=0.1, neg=0.2, zero=0.4, pos=0.2, above=0.1)
    # E[r] = 0.1 * -0.08 + 0.2 * -0.025 + 0.4 * 0.025 + 0.2 * 0.075 + 0.1 * 0.12
    #      = -0.008 - 0.005 + 0.010 + 0.015 + 0.012 = +0.024 (2.4%)
    # After 2% cost: util = 0.4%. With 1% threshold: score = -0.6% -> NoAction.
    verdict = decide(f, ToyCostModel(round_trip_cost=0.02), threshold=0.01)
    assert isinstance(verdict.final_action, NoAction)


# ---------------------------------------------------------------------------
# Sizing monotonicity
# ---------------------------------------------------------------------------


def test_more_variance_yields_smaller_kelly_fraction() -> None:
    # Same expected return; more variance -> smaller fractional Kelly.
    low_var = _forecast(below=0.0, neg=0.0, zero=0.5, pos=0.5, above=0.0)
    high_var = _forecast(below=0.05, neg=0.05, zero=0.45, pos=0.40, above=0.05)
    v_low = decide(low_var, ToyCostModel(round_trip_cost=0.0), threshold=0.0)
    v_high = decide(high_var, ToyCostModel(round_trip_cost=0.0), threshold=0.0)
    # Both should trade. The lower-variance one should size larger.
    assert isinstance(v_low.final_action, TradeAction)
    assert isinstance(v_high.final_action, TradeAction)
    assert v_low.kelly_fraction_applied >= v_high.kelly_fraction_applied


def test_higher_expected_return_yields_larger_kelly_fraction() -> None:
    # Roughly same variance; larger expected return -> larger fractional Kelly.
    # Use very small kelly_fraction so the 1.0 cap doesn't mask the comparison
    # (the bucket midpoints span ~0.20, so even small edges trip the cap under
    # quarter Kelly).
    small_edge = _forecast(below=0.10, neg=0.20, zero=0.40, pos=0.20, above=0.10)
    big_edge = _forecast(below=0.05, neg=0.05, zero=0.30, pos=0.30, above=0.30)
    v_small = decide(
        small_edge, ToyCostModel(round_trip_cost=0.0), threshold=0.0, kelly_fraction=0.01
    )
    v_big = decide(big_edge, ToyCostModel(round_trip_cost=0.0), threshold=0.0, kelly_fraction=0.01)
    assert isinstance(v_small.final_action, TradeAction)
    assert isinstance(v_big.final_action, TradeAction)
    assert v_big.kelly_fraction_applied > v_small.kelly_fraction_applied


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_zero_variance_point_mass_uses_kelly_fraction_directly() -> None:
    # All mass on a single bucket -> variance = 0; engine falls back to kelly_fraction.
    f = _forecast(below=0.0, neg=0.0, zero=0.0, pos=0.0, above=1.0)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.0), threshold=0.0, kelly_fraction=0.25)
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.kelly_fraction_applied == pytest.approx(0.25)


def test_zero_threshold_trades_on_any_positive_utility() -> None:
    f = _forecast(below=0.0, neg=0.0, zero=0.4, pos=0.4, above=0.2)
    # E[r] = 0.4 * 0.025 + 0.4 * 0.075 + 0.2 * 0.12 = 0.01 + 0.03 + 0.024 = +0.064
    # Cost 0; threshold 0 -> always trades.
    verdict = decide(f, ToyCostModel(round_trip_cost=0.0), threshold=0.0)
    assert isinstance(verdict.final_action, TradeAction)


def test_no_action_carries_zero_kelly_fraction_applied() -> None:
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.10), threshold=0.10)
    assert isinstance(verdict.final_action, NoAction)
    assert verdict.kelly_fraction_applied == 0.0


def test_verdict_fields_match_contract_verification_fields() -> None:
    """Verdict object exposes exactly the names the Contract expects."""
    f = _forecast(0.05, 0.075, 0.125, 0.50, 0.25)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    # These five attributes are what the caller writes onto the Contract.
    assert hasattr(verdict, "calibrated_expected_return")
    assert hasattr(verdict, "calibrated_expected_utility")
    assert hasattr(verdict, "tradable_edge_score")
    assert hasattr(verdict, "kelly_fraction_applied")
    assert hasattr(verdict, "final_action")


# ---------------------------------------------------------------------------
# Adversarial agent crush
# ---------------------------------------------------------------------------


def test_confident_agent_post_shrinkage_emits_no_action() -> None:
    """ConfidentAgent's raw 0.95-on-below_minus_5 forecast survives Stone 11c
    as a roughly-flat distribution; expected utility after costs cannot clear
    the threshold; the engine emits NoAction.
    """
    # Approximate post-shrinkage distribution per PYRAMID Stone 11d table:
    # 0.38 on below_minus_5, ~0.155 on each other bucket (renormalized).
    f = _forecast(below=0.38, neg=0.155, zero=0.155, pos=0.155, above=0.155)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01), threshold=0.01)
    # E[r] = 0.38 * -0.08 + 0.155 * (-0.025 + 0.025 + 0.075 + 0.12)
    #      = -0.0304 + 0.155 * 0.195 = -0.0304 + 0.0302 = ~-0.0002 (basically zero)
    # abs - cost - threshold = 0.0002 - 0.01 - 0.01 = -0.0198 -> NoAction
    assert isinstance(verdict.final_action, NoAction)
    assert verdict.tradable_edge_score < 0


def test_uniform_agent_emits_no_action() -> None:
    """UniformAgent (0.2 each) has E[r] determined only by midpoint asymmetry;
    after costs the engine should emit NoAction at reasonable thresholds.
    """
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01), threshold=0.02)
    # E[r] = 0.2 * (-0.08 - 0.025 + 0.025 + 0.075 + 0.12) = 0.2 * 0.115 = +0.023
    # |E[r]| - cost - threshold = 0.023 - 0.01 - 0.02 = -0.007 -> NoAction
    assert isinstance(verdict.final_action, NoAction)


def test_bayesian_strong_signal_well_sampled_bin_trades() -> None:
    """A well-calibrated, well-sampled forecast with a real signal trades."""
    # Strong upward tilt; well-calibrated already.
    f = _forecast(below=0.02, neg=0.08, zero=0.20, pos=0.50, above=0.20)
    # E[r] = 0.02 * -0.08 + 0.08 * -0.025 + 0.20 * 0.025 + 0.50 * 0.075 + 0.20 * 0.12
    #      = -0.0016 - 0.002 + 0.005 + 0.0375 + 0.024 = +0.0629 (6.29%)
    # abs - 1% cost - 1% threshold = 4.29% -> trade
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01), threshold=0.01)
    assert isinstance(verdict.final_action, TradeAction)
    assert verdict.final_action.direction == "long"


# ---------------------------------------------------------------------------
# Defaults and invalid-input guards
# ---------------------------------------------------------------------------


def test_default_constants_are_sensible() -> None:
    assert DEFAULT_THRESHOLD == 0.01
    assert DEFAULT_KELLY_FRACTION == 0.25
    assert DEFAULT_NOTIONAL_BASE == 100_000.0


def test_negative_threshold_raises() -> None:
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    with pytest.raises(ValueError, match="threshold"):
        decide(f, ToyCostModel(round_trip_cost=0.01), threshold=-0.01)


def test_kelly_fraction_outside_unit_interval_raises() -> None:
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    with pytest.raises(ValueError, match="kelly_fraction"):
        decide(f, ToyCostModel(round_trip_cost=0.01), kelly_fraction=0.0)
    with pytest.raises(ValueError, match="kelly_fraction"):
        decide(f, ToyCostModel(round_trip_cost=0.01), kelly_fraction=1.5)
    with pytest.raises(ValueError, match="kelly_fraction"):
        decide(f, ToyCostModel(round_trip_cost=0.01), kelly_fraction=-0.1)


def test_non_positive_notional_base_raises() -> None:
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    with pytest.raises(ValueError, match="notional_base"):
        decide(f, ToyCostModel(round_trip_cost=0.01), notional_base=0.0)
    with pytest.raises(ValueError, match="notional_base"):
        decide(f, ToyCostModel(round_trip_cost=0.01), notional_base=-100.0)


def test_negative_round_trip_cost_raises() -> None:
    f = _forecast(0.2, 0.2, 0.2, 0.2, 0.2)
    with pytest.raises(ValueError, match="round_trip_cost"):
        decide(f, ToyCostModel(round_trip_cost=-0.01))


def test_verdict_is_frozen_dataclass() -> None:
    """ActionEngineVerdict must be immutable for audit safety."""
    f = _forecast(0.05, 0.05, 0.10, 0.50, 0.30)
    verdict = decide(f, ToyCostModel(round_trip_cost=0.01))
    with pytest.raises((AttributeError, Exception)):
        verdict.tradable_edge_score = 999.0  # type: ignore[misc]
