"""Stone 18: reliability diagrams as the visual Phase 0 exit criterion.

Asserts the structural shapes of each agent's reliability diagram. These
properties must hold for the Phase 0 exit criterion (per BUILD.md):

  - ConfidentAgent shows OVERCONFIDENCE: a populated high-claim bucket
    whose observed rate is far below the claim.
  - UniformAgent shows ZERO DISCRIMINATION: only one bucket populated;
    that bucket's claim and observed rate are both near 0.333.
  - BayesianAgent shows DISCRIMINATION + CALIBRATION: many buckets
    populated, each close to the 45° calibration line.

PYRAMID.md Stone 18 documents the visual reading; this test locks the
underlying numerical structure in as a CI gate.
"""

from __future__ import annotations

import pytest

from fingym.evaluator.scoring import ReliabilityBucket
from fingym.toys.reliability_diagrams import compute_reliability_data

CONFIDENT = "ConfidentAgent(decaying, p=0.95)"
UNIFORM = "UniformAgent"
BAYESIAN = "BayesianAgent"
MARKET = "Market"


@pytest.fixture(scope="module")
def reliability() -> dict[str, list[ReliabilityBucket]]:
    """100-episode reliability data at base_seed=42, computed once per module."""
    return compute_reliability_data(
        n_episodes=100, n_emissions_per_episode=12, base_seed=42, n_buckets=10
    )


def test_confident_agent_shows_overconfidence(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """Confident's high-claim bucket [0.9, 1.0] has many predictions but observed
    rate far below the claim. Decaying happens ~1/3 of the time, but the agent
    claims ~95% on it every prediction → overconfidence."""
    high_buckets = [b for b in reliability[CONFIDENT] if b.lo >= 0.9]
    assert len(high_buckets) >= 1, "ConfidentAgent should have a high-claim bucket"
    high = high_buckets[0]
    assert high.count >= 100, "high-claim bucket should be heavily populated"
    assert high.mean_claim > 0.9
    assert high.observed_rate < 0.5
    # Gap: claim >> observed (the signature of overconfidence)
    assert high.mean_claim - high.observed_rate > 0.4


def test_confident_agent_low_claim_bucket_shows_underconfidence(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """Confident's low-claim bucket [0.0, 0.1) has many predictions (P=0.025 on
    strg and stbl) but observed rate ~0.33 (those states happen ~1/3 each).
    Claim << observed → underconfidence on the rest of the state space."""
    low_buckets = [b for b in reliability[CONFIDENT] if b.hi <= 0.1]
    assert len(low_buckets) >= 1, "ConfidentAgent should have a low-claim bucket"
    low = low_buckets[0]
    assert low.mean_claim < 0.1
    assert low.observed_rate > 0.2
    # Gap: observed >> claim
    assert low.observed_rate - low.mean_claim > 0.2


def test_uniform_agent_has_no_discrimination(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """UniformAgent emits the same belief on every tick, so only ONE bucket
    is populated — the one containing 0.333. That bucket sits near the
    diagonal but the absence of any other populated bucket is itself the
    failure mode: the agent has no discrimination across confidence levels."""
    buckets = reliability[UNIFORM]
    assert len(buckets) == 1, "UniformAgent should populate exactly one bucket"
    only = buckets[0]
    assert 0.3 <= only.mean_claim < 0.4
    # On the diagonal (within tolerance) — uniform belief over 3 states with
    # uniformly-distributed truth yields observed rate ≈ 1/3.
    assert abs(only.mean_claim - only.observed_rate) < 0.05


def test_bayesian_agent_has_discrimination_and_calibration(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """BayesianAgent populates multiple buckets across the [0, 1] range
    (discrimination) AND each populated bucket sits close to the diagonal
    (calibration). Tolerance: 0.15 (broadly-calibrated, sample-noisy)."""
    buckets = reliability[BAYESIAN]
    assert len(buckets) >= 3, "BayesianAgent should populate multiple buckets"
    for b in buckets:
        # Skip very-small-count buckets where sample noise dominates
        if b.count < 50:
            continue
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 0.15, (
            f"Bayesian bucket [{b.lo:.2f}, {b.hi:.2f}) has gap {gap:.3f} "
            f"(mean_claim {b.mean_claim:.3f} vs observed {b.observed_rate:.3f}); "
            f"expected gap < 0.15"
        )


def test_market_shows_discrimination_and_calibration(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """Market is a BayesianAgent with the Stone 11a market prior; same
    properties as BayesianAgent — multi-bucket discrimination, calibrated.
    """
    buckets = reliability[MARKET]
    assert len(buckets) >= 3
    for b in buckets:
        if b.count < 50:
            continue
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 0.15, f"Market bucket [{b.lo:.2f}, {b.hi:.2f}) has gap {gap:.3f}"
