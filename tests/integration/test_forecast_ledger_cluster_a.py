"""Phase 1 NEW Cluster A end-to-end: toy → agents → Forecast Ledger.

Locks in the Cluster A exit criterion (PYRAMID Stone 11b, BUILD.md Phase 1
NEW Cluster A): three adversarial agents (Confident, Uniform, Bayesian)
each record their final per-episode forecast into a shared Forecast Ledger,
keyed by `signal_class_id`. The Ledger's `reliability_for_signal_class`
view discriminates the three:

  - ConfidentAgent ("confident_static") — high-claim bucket far below the
    diagonal (overconfidence) AND low-claim bucket far above (underconfidence
    on the rest of the bucket space). This is the same overconfidence
    signature surfaced by Stone 18's reliability diagrams, but per signal
    class.
  - UniformAgent ("uniform_static") — only one populated bucket (zero
    discrimination), and that bucket sits exactly on the diagonal (mean
    claim = observed rate = 1/N_BUCKETS = 0.2 by symmetry).
  - BayesianAgent ("bayesian_3state_toy") — multiple buckets populated
    across [0, 1] (discrimination) and broadly close to the diagonal
    (calibration).

Signal class isolation is also locked in: distinct ids appear in the Ledger;
records under one id do not leak into another's reliability view.

This is the Phase 1 NEW Cluster A exit gate — the proof that the toy +
agents + Ledger pipeline produces empirically distinguishable reliability
signatures per signal class. Cluster B's calibration shrinkage consumes the
exact view this test pins down.
"""

from __future__ import annotations

import random

import pytest

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
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
)

CONFIDENT_SCI = "confident_static"
UNIFORM_SCI = "uniform_static"
BAYESIAN_SCI = "bayesian_3state_toy"


@pytest.fixture(scope="module")
def populated_ledger() -> ForecastLedger:
    """Run 100 episodes through all three adversarial agents; record each
    agent's final per-episode forecast into a shared Forecast Ledger,
    tagged by `signal_class_id`. Returns the populated Ledger."""
    n_episodes = 100
    n_emissions_per_episode = 12
    base_seed = 42

    state_rng = random.Random(base_seed)
    state_choices: list[CompanyState] = list(STATES)
    ledger = ForecastLedger()

    for episode_idx in range(n_episodes):
        truth_state = state_rng.choice(state_choices)
        episode_seed = base_seed + episode_idx + 1
        episode_rng = random.Random(episode_seed)

        confident = ConfidentAgent("below_minus_5", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
        all_actors: list[Agent] = [confident, uniform, bayesian]

        for _ in range(n_emissions_per_episode):
            emission = sample_emission(truth_state, episode_rng)
            for a in all_actors:
                a.observe(emission)

        realized_return = realize_return_at_horizon(truth_state, episode_rng)
        realized_bucket = return_to_bucket(realized_return)

        for a in all_actors:
            ledger.record(a.signal_class_id, a.forecast, realized_bucket)

    return ledger


# ---------------------------------------------------------------------------
# Ledger accounting / isolation.
# ---------------------------------------------------------------------------


def test_ledger_records_all_three_signal_classes(populated_ledger: ForecastLedger) -> None:
    """All three signal_class_ids appear in the Ledger; one record per agent
    per episode = 100 records each = 300 total."""
    sci_set = set(populated_ledger.all_signal_classes())
    assert sci_set == {CONFIDENT_SCI, UNIFORM_SCI, BAYESIAN_SCI}
    assert populated_ledger.records_for_signal_class(CONFIDENT_SCI) == 100
    assert populated_ledger.records_for_signal_class(UNIFORM_SCI) == 100
    assert populated_ledger.records_for_signal_class(BAYESIAN_SCI) == 100
    assert populated_ledger.total_records() == 300


# ---------------------------------------------------------------------------
# ConfidentAgent — overconfidence signature.
# ---------------------------------------------------------------------------


def test_confident_signal_class_shows_overconfidence(
    populated_ledger: ForecastLedger,
) -> None:
    """The high-claim bucket [0.9, 1.0] under `confident_static` has many
    pairs but observed rate far below the claim. Concretely, the agent claims
    P=0.95 on `below_minus_5` every episode; `below_minus_5` realizes only
    ~25% of the time across uniformly-mixed states."""
    buckets = populated_ledger.reliability_for_signal_class(CONFIDENT_SCI, n_buckets=10)
    high = next(b for b in buckets if b.lo >= 0.9)
    assert high.count == 100, "one high-claim pair per episode"
    assert high.mean_claim > 0.9
    assert high.observed_rate < 0.5
    assert high.mean_claim - high.observed_rate > 0.4


def test_confident_signal_class_low_claim_shows_underconfidence(
    populated_ledger: ForecastLedger,
) -> None:
    """The low-claim bucket [0.0, 0.1) under `confident_static` has 4
    (claim, outcome) pairs per episode at claim ≈ 0.0125. Observed rate is
    the average frequency of the four non-target buckets, which averages
    ~19%. Claim ≪ observed → underconfidence."""
    buckets = populated_ledger.reliability_for_signal_class(CONFIDENT_SCI, n_buckets=10)
    low = next(b for b in buckets if b.hi <= 0.1)
    assert low.count == 400, "four low-claim pairs per episode x 100 episodes"
    assert low.mean_claim < 0.1
    assert low.observed_rate > 0.10
    assert low.observed_rate - low.mean_claim > 0.10


# ---------------------------------------------------------------------------
# UniformAgent — zero discrimination signature.
# ---------------------------------------------------------------------------


def test_uniform_signal_class_has_one_bucket_on_diagonal(
    populated_ledger: ForecastLedger,
) -> None:
    """UniformAgent claims 0.2 per bucket every episode, so only one
    reliability bucket is populated — the one containing 0.2. By symmetry
    (5 buckets, exactly one realized per episode), observed rate is also
    0.2 exactly. The single-populated-bucket shape is the failure signature:
    no discrimination across confidence levels."""
    buckets = populated_ledger.reliability_for_signal_class(UNIFORM_SCI, n_buckets=10)
    assert len(buckets) == 1, "UniformAgent populates exactly one reliability bucket"
    only = buckets[0]
    assert only.count == 500, "5 pairs per episode x 100 episodes"
    assert 0.2 <= only.mean_claim < 0.3
    assert abs(only.mean_claim - only.observed_rate) < 1e-9


# ---------------------------------------------------------------------------
# BayesianAgent — discrimination + broad calibration.
# ---------------------------------------------------------------------------


def test_bayesian_signal_class_shows_discrimination(
    populated_ledger: ForecastLedger,
) -> None:
    """BayesianAgent populates many reliability buckets across [0, 1] — the
    final per-episode forecast varies, so different episodes contribute
    pairs at different claim levels. Discrimination = the agent emits
    distinguishable confidence levels, not the single point UniformAgent
    emits."""
    buckets = populated_ledger.reliability_for_signal_class(BAYESIAN_SCI, n_buckets=10)
    # Count >= 15 filters out near-empty buckets where two or three pairs
    # would be sample noise. Even at this threshold we expect ≥5 populated
    # buckets, proving the agent emits a spread of confidence levels.
    populated = [b for b in buckets if b.count >= 15]
    assert len(populated) >= 5, (
        f"BayesianAgent should populate ≥5 reliability buckets with count ≥ 15; "
        f"got {len(populated)} buckets: "
        f"{[(round(b.lo, 1), b.count) for b in populated]}"
    )


def test_bayesian_signal_class_well_sampled_buckets_are_calibrated(
    populated_ledger: ForecastLedger,
) -> None:
    """BayesianAgent's well-sampled reliability buckets (count ≥ 50) sit
    close to the diagonal (broad calibration).

    Tolerance: 0.15 for well-sampled buckets. Mid-sampled buckets (15 ≤
    count < 50) are looser at the extremes because the Bayes update treats
    emissions as conditionally independent given the BUCKET, but the true
    generating process makes them conditionally independent given the
    STATE. This mild mis-specification produces extreme-claim overconfidence
    in the agent's posterior — precisely the failure mode the Cluster B
    calibration shrinkage corrects via empirical Ledger reliability. The
    well-sampled buckets (the bulk of the mass) are calibrated; the
    extremes are noisy but bounded."""
    buckets = populated_ledger.reliability_for_signal_class(BAYESIAN_SCI, n_buckets=10)
    well_sampled = [b for b in buckets if b.count >= 50]
    assert len(well_sampled) >= 2, (
        f"BayesianAgent should have ≥2 well-sampled (count ≥ 50) buckets; got {len(well_sampled)}"
    )
    for b in well_sampled:
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 0.15, (
            f"Well-sampled Bayesian bucket [{b.lo:.2f}, {b.hi:.2f}) has gap "
            f"{gap:.3f} (mean_claim {b.mean_claim:.3f} vs observed {b.observed_rate:.3f}); "
            f"expected gap < 0.15"
        )
    # Mid-sampled buckets — broader tolerance to absorb extreme-claim
    # overconfidence; Cluster B's shrinkage will tighten this further.
    mid_sampled = [b for b in buckets if 15 <= b.count < 50]
    for b in mid_sampled:
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 0.35, (
            f"Mid-sampled Bayesian bucket [{b.lo:.2f}, {b.hi:.2f}) has gap "
            f"{gap:.3f} (mean_claim {b.mean_claim:.3f} vs observed {b.observed_rate:.3f}); "
            f"expected gap < 0.35"
        )


# ---------------------------------------------------------------------------
# Cross-signal-class isolation.
# ---------------------------------------------------------------------------


def test_signal_class_views_are_isolated(populated_ledger: ForecastLedger) -> None:
    """The three reliability views differ in shape, confirming no
    cross-contamination across signal classes. Specifically: UniformAgent's
    view has exactly one populated bucket; ConfidentAgent's has two clusters
    (a heavily-populated high-claim and a heavily-populated low-claim);
    BayesianAgent's has many."""
    confident_buckets = populated_ledger.reliability_for_signal_class(CONFIDENT_SCI)
    uniform_buckets = populated_ledger.reliability_for_signal_class(UNIFORM_SCI)
    bayesian_buckets = populated_ledger.reliability_for_signal_class(BAYESIAN_SCI)

    # Confident: high-claim + low-claim clusters dominate; total populated
    # buckets is 2 (the rest of the [0, 1] range gets no pairs at all because
    # the agent only ever emits 0.95 or 0.0125).
    confident_populated = [b for b in confident_buckets if b.count > 0]
    assert len(confident_populated) == 2, (
        f"ConfidentAgent should have 2 populated reliability buckets; "
        f"got {len(confident_populated)}"
    )

    # Uniform: exactly 1.
    assert len(uniform_buckets) == 1

    # Bayesian: at least 5 populated buckets at count ≥ 15 — the agent's
    # final-per-episode forecast varies, so different episodes contribute
    # pairs at different claim levels.
    bayesian_populated = [b for b in bayesian_buckets if b.count >= 15]
    assert len(bayesian_populated) >= 5
