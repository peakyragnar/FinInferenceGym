"""Stone 18: reliability diagrams as the visual Phase 0 exit criterion.

Asserts the structural shapes of each agent's reliability diagram. These
properties must hold for the Phase 0 exit criterion (per BUILD.md):

  - ConfidentAgent shows OVERCONFIDENCE: a populated high-claim bucket
    whose observed rate is far below the claim.
  - UniformAgent shows ZERO DISCRIMINATION: only one bucket populated;
    that bucket's claim and observed rate are both near 1/N_BUCKETS = 0.2.
  - BayesianAgent shows DISCRIMINATION + CALIBRATION: many buckets
    populated, each broadly close to the 45° calibration line.

Phase 1 NEW Cluster A: agents now emit forecasts over realized-return
BUCKETS, not state beliefs. UniformAgent emits 0.2 per bucket (1/5) and
ConfidentAgent claims 0.95 on `below_minus_5`. Calibration tolerance for
BayesianAgent is looser than in the 3-state setup because bucket-conditional
likelihoods marginalize over states and are intrinsically less discriminating.

PYRAMID.md Stone 18 documents the visual reading; this test locks the
underlying numerical structure in as a CI gate.
"""

from __future__ import annotations

import pytest

from fingym.evaluator.scoring import ReliabilityBucket
from fingym.toys.reliability_diagrams import compute_reliability_data

CONFIDENT = "ConfidentAgent(below_minus_5, p=0.95)"
UNIFORM = "UniformAgent"
BAYESIAN = "BayesianAgent"


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
    rate far below the claim. The realized log return falls in `below_minus_5`
    only ~25% of the time across uniformly-mixed states, but the agent claims
    ~95% on it every tick → overconfidence."""
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
    """Confident's low-claim bucket [0.0, 0.1) has many predictions (P=0.0125 on
    each of the four non-target buckets) but the observed rate averages ~0.19
    (each of those buckets happens ~19% of the time on average across mixed
    states). Claim << observed → underconfidence on the rest of the bucket
    space."""
    low_buckets = [b for b in reliability[CONFIDENT] if b.hi <= 0.1]
    assert len(low_buckets) >= 1, "ConfidentAgent should have a low-claim bucket"
    low = low_buckets[0]
    assert low.mean_claim < 0.1
    assert low.observed_rate > 0.10
    # Gap: observed >> claim
    assert low.observed_rate - low.mean_claim > 0.10


def test_uniform_agent_has_no_discrimination(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """UniformAgent emits the same forecast on every tick — 1/N_BUCKETS = 0.2
    on each of the 5 buckets. So only ONE claim bucket is populated, the one
    containing 0.2. That bucket sits exactly on the diagonal (observed rate
    also = 0.2 by symmetry), but the absence of any other populated bucket
    is itself the failure mode: no discrimination across confidence levels."""
    buckets = reliability[UNIFORM]
    assert len(buckets) == 1, "UniformAgent should populate exactly one bucket"
    only = buckets[0]
    assert 0.2 <= only.mean_claim < 0.3
    # On the diagonal — uniform forecast over N buckets with realized bucket
    # drawn from the marginal distribution yields observed rate = 1/N exactly.
    assert abs(only.mean_claim - only.observed_rate) < 0.05


def test_bayesian_agent_has_discrimination_and_calibration(
    reliability: dict[str, list[ReliabilityBucket]],
) -> None:
    """BayesianAgent populates multiple buckets across the [0, 1] range
    (discrimination) AND each populated bucket sits broadly close to the
    diagonal (calibration).

    Tolerance: 0.30 (broad). Under Phase 1 NEW Cluster A, the agent's
    hypothesis space is realized-return buckets; its update uses
    bucket-conditional emission likelihoods that marginalize over the
    underlying state structure. Because the true generating process makes
    emissions conditionally independent given the STATE — not the bucket —
    the agent's Bayes update implicitly treats correlated emissions as
    independent evidence, mildly overweighting them. Concretely, the
    top-claim bucket [0.9, 1.0] tends to overshoot observed frequency by
    ~0.25. This is EXPECTED and the precise failure the Forecast Ledger
    (Phase 1 NEW Cluster B) was introduced to correct via empirical
    shrinkage. For Phase 0 we lock in: many populated buckets +
    broadly-on-diagonal calibration."""
    buckets = reliability[BAYESIAN]
    assert len(buckets) >= 3, "BayesianAgent should populate multiple buckets"
    for b in buckets:
        # Skip very-small-count buckets where sample noise dominates
        if b.count < 50:
            continue
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 0.30, (
            f"Bayesian bucket [{b.lo:.2f}, {b.hi:.2f}) has gap {gap:.3f} "
            f"(mean_claim {b.mean_claim:.3f} vs observed {b.observed_rate:.3f}); "
            f"expected gap < 0.30"
        )


# The pre-v5 `test_market_shows_discrimination_and_calibration` test was
# removed by the Constitution v5 cleanup pass alongside the Market-as-second-
# Bayesian-believer setup. Under v5 the Market-State Baseline is an isolated
# control (`src/fingym/baseline/`) with its own reliability tracking; the
# integration test for that lands when Stone 11e is taught.
