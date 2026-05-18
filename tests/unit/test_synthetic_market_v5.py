"""Unit tests for the v5 additions to synthetic_market.py.

Covers the new primitives added in Phase 1 NEW Cluster A (Stones 7b, 11b):

  - realize_return_at_horizon — state-conditional realized log-return sampling
  - return_to_bucket — log-return → bucket mapping
  - bucket-conditional likelihoods — P(emission | bucket), derived from the
    toy's state structure
  - update_forecast_over_buckets — Bayesian update on the bucket hypothesis space

These tests validate the new toy primitives without exercising the full agent
pipeline; the end-to-end pipeline is tested separately.
"""

from __future__ import annotations

import math
import random

import pytest

from fingym.toys.synthetic_market import (
    BUCKET_CONDITIONAL_LIKELIHOODS,
    EMISSIONS,
    RETURN_BUCKETS,
    STATE_RETURN_PARAMS,
    STATES,
    CompanyState,
    ReturnBucket,
    bucket_likelihood,
    realize_return_at_horizon,
    return_to_bucket,
    uniform_forecast_over_buckets,
    update_forecast_over_buckets,
)

# ---------------------------------------------------------------------------
# return_to_bucket — bucket mapping.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("log_return", "expected_bucket"),
    [
        (-0.10, "below_minus_5"),
        (-0.0501, "below_minus_5"),
        (-0.05, "minus_5_to_0"),
        (-0.0001, "minus_5_to_0"),
        (0.0, "zero_to_plus_5"),
        (0.0499, "zero_to_plus_5"),
        (0.05, "plus_5_to_plus_10"),
        (0.0999, "plus_5_to_plus_10"),
        (0.10, "above_plus_10"),
        (0.50, "above_plus_10"),
    ],
)
def test_return_to_bucket_maps_log_returns_to_correct_buckets(
    log_return: float, expected_bucket: ReturnBucket
) -> None:
    """Each log return should land in the correct bucket per the boundaries
    -0.05 / 0 / +0.05 / +0.10."""
    assert return_to_bucket(log_return) == expected_bucket


# ---------------------------------------------------------------------------
# realize_return_at_horizon — state-conditional realized log returns.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", list(STATES))
def test_realized_returns_match_state_distribution_empirically(state: CompanyState) -> None:
    """Sampling many realized returns from a state should match its N(mean, std)
    parameters within tolerance for sample size."""
    rng = random.Random(42)
    n_samples = 10_000
    samples = [realize_return_at_horizon(state, rng) for _ in range(n_samples)]
    empirical_mean = sum(samples) / n_samples
    empirical_var = sum((s - empirical_mean) ** 2 for s in samples) / (n_samples - 1)
    empirical_std = math.sqrt(empirical_var)

    expected_mean, expected_std = STATE_RETURN_PARAMS[state]
    # Tolerances calibrated for n=10000 with the given std (around 4%).
    assert abs(empirical_mean - expected_mean) < 0.002, (
        f"State {state}: empirical mean {empirical_mean:.4f} != expected {expected_mean:.4f}"
    )
    assert abs(empirical_std - expected_std) < 0.002, (
        f"State {state}: empirical std {empirical_std:.4f} != expected {expected_std:.4f}"
    )


# ---------------------------------------------------------------------------
# bucket-conditional likelihoods — sanity properties.
# ---------------------------------------------------------------------------


def test_bucket_conditional_likelihoods_are_valid_distributions() -> None:
    """For each bucket, P(emission | bucket) over all emissions must sum to ~1."""
    for bucket in RETURN_BUCKETS:
        probs = [BUCKET_CONDITIONAL_LIKELIHOODS[bucket][e] for e in EMISSIONS]
        assert all(0.0 <= p <= 1.0 for p in probs), (
            f"Bucket {bucket}: probabilities not in [0, 1]: {probs}"
        )
        assert abs(sum(probs) - 1.0) < 1e-9, f"Bucket {bucket}: probabilities sum to {sum(probs)}"


def test_lowest_bucket_favors_weak_emissions() -> None:
    """The lowest return bucket (below -5%) is most associated with the decaying
    state, which emits 'weak' 70% of the time. So P(weak | below_minus_5) should
    exceed P(strong | below_minus_5)."""
    p_strong = bucket_likelihood("strong", "below_minus_5")
    p_weak = bucket_likelihood("weak", "below_minus_5")
    assert p_weak > p_strong, (
        f"In below_minus_5 bucket: P(weak)={p_weak:.3f} should exceed P(strong)={p_strong:.3f}"
    )


def test_highest_bucket_favors_strong_emissions() -> None:
    """The highest return bucket (above +10%) is most associated with strengthening,
    which emits 'strong' 70% of the time. So P(strong | above_plus_10) should
    exceed P(weak | above_plus_10)."""
    p_strong = bucket_likelihood("strong", "above_plus_10")
    p_weak = bucket_likelihood("weak", "above_plus_10")
    assert p_strong > p_weak, (
        f"In above_plus_10 bucket: P(strong)={p_strong:.3f} should exceed P(weak)={p_weak:.3f}"
    )


# ---------------------------------------------------------------------------
# update_forecast_over_buckets — Bayesian update on the bucket hypothesis space.
# ---------------------------------------------------------------------------


def test_update_preserves_distribution_sum_to_1() -> None:
    """After any Bayes update, the posterior should still sum to 1."""
    forecast = uniform_forecast_over_buckets()
    for emission in EMISSIONS:
        forecast = update_forecast_over_buckets(forecast, emission)
        total = sum(forecast.values())
        assert abs(total - 1.0) < 1e-9, f"After {emission}, distribution sums to {total}"


def test_strong_emission_shifts_forecast_upward() -> None:
    """A 'strong' emission should make the agent more confident in higher-return
    buckets. Specifically, P(above_plus_10) should rise after a 'strong' emission
    from a uniform prior."""
    prior = uniform_forecast_over_buckets()
    posterior = update_forecast_over_buckets(prior, "strong")
    assert posterior["above_plus_10"] > prior["above_plus_10"], (
        f"After 'strong' emission: P(above_plus_10) went from "
        f"{prior['above_plus_10']:.3f} to {posterior['above_plus_10']:.3f} (should rise)"
    )
    assert posterior["below_minus_5"] < prior["below_minus_5"], (
        f"After 'strong' emission: P(below_minus_5) went from "
        f"{prior['below_minus_5']:.3f} to {posterior['below_minus_5']:.3f} (should fall)"
    )


def test_weak_emission_shifts_forecast_downward() -> None:
    """A 'weak' emission should make the agent more confident in lower-return
    buckets. P(below_minus_5) should rise after a 'weak' emission."""
    prior = uniform_forecast_over_buckets()
    posterior = update_forecast_over_buckets(prior, "weak")
    assert posterior["below_minus_5"] > prior["below_minus_5"], (
        f"After 'weak' emission: P(below_minus_5) went from "
        f"{prior['below_minus_5']:.3f} to {posterior['below_minus_5']:.3f} (should rise)"
    )
    assert posterior["above_plus_10"] < prior["above_plus_10"], (
        f"After 'weak' emission: P(above_plus_10) went from "
        f"{prior['above_plus_10']:.3f} to {posterior['above_plus_10']:.3f} (should fall)"
    )


def test_repeated_strong_emissions_concentrate_belief_at_top() -> None:
    """After many 'strong' emissions, belief should concentrate on above_plus_10
    (the bucket most associated with strengthening which emits strong)."""
    forecast = uniform_forecast_over_buckets()
    for _ in range(20):
        forecast = update_forecast_over_buckets(forecast, "strong")
    # The probability on above_plus_10 should be a meaningful majority.
    assert forecast["above_plus_10"] > 0.5, (
        f"After 20 'strong' emissions, P(above_plus_10) = "
        f"{forecast['above_plus_10']:.3f} (expected > 0.5)"
    )
