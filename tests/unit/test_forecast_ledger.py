"""Unit tests for the Forecast Ledger MVP (Stone 11b).

Covers the in-memory append-only Ledger built in Phase 1 NEW Cluster A:

  - record + audit accessors (records_for_signal_class, all_signal_classes,
    total_records) accumulate correctly across mixed signal classes
  - record snapshots forecasts (caller mutation does not poison history)
  - reliability_for_signal_class returns the standard reliability bucketing
  - reliability is computed per signal class — entries under one id do not
    leak into another's reliability
  - an unknown signal class returns []
  - a perfectly calibrated stream produces points on the diagonal
  - a confidently-wrong stream produces large (claim - observed) gaps in the
    high-claim bucket and large (observed - claim) gaps in the low-claim
    bucket

End-to-end Ledger behavior against full adversarial agents is locked in by
the integration test in `tests/integration/test_forecast_ledger_cluster_a.py`.
"""

from __future__ import annotations

import pytest

from fingym.ledger.forecast_ledger import ForecastLedger
from fingym.toys.synthetic_market import RETURN_BUCKETS, ReturnBucket

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _uniform() -> dict[ReturnBucket, float]:
    return {b: 1.0 / len(RETURN_BUCKETS) for b in RETURN_BUCKETS}


def _degenerate_on(target: ReturnBucket) -> dict[ReturnBucket, float]:
    """A forecast putting essentially all mass on `target` (with small floor)."""
    floor = 1e-6
    other_count = len(RETURN_BUCKETS) - 1
    mass = 1.0 - floor * other_count
    return {b: (mass if b == target else floor) for b in RETURN_BUCKETS}


# ---------------------------------------------------------------------------
# record + audit accessors.
# ---------------------------------------------------------------------------


def test_empty_ledger_has_no_records_no_signal_classes() -> None:
    """Fresh ledger reports zero records, zero signal classes."""
    ledger = ForecastLedger()
    assert ledger.total_records() == 0
    assert ledger.all_signal_classes() == []
    assert ledger.records_for_signal_class("anything") == 0


def test_record_increments_counters_per_signal_class() -> None:
    """Records under different signal classes accumulate independently."""
    ledger = ForecastLedger()
    ledger.record("sig_a", _uniform(), "zero_to_plus_5")
    ledger.record("sig_a", _uniform(), "below_minus_5")
    ledger.record("sig_b", _uniform(), "above_plus_10")
    assert ledger.total_records() == 3
    assert ledger.records_for_signal_class("sig_a") == 2
    assert ledger.records_for_signal_class("sig_b") == 1
    assert ledger.records_for_signal_class("sig_unknown") == 0


def test_all_signal_classes_returns_first_seen_order() -> None:
    """Distinct ids are returned in the order they first appear."""
    ledger = ForecastLedger()
    ledger.record("sig_b", _uniform(), "zero_to_plus_5")
    ledger.record("sig_a", _uniform(), "zero_to_plus_5")
    ledger.record("sig_b", _uniform(), "below_minus_5")
    ledger.record("sig_c", _uniform(), "above_plus_10")
    assert ledger.all_signal_classes() == ["sig_b", "sig_a", "sig_c"]


def test_record_snapshots_forecast_against_caller_mutation() -> None:
    """Mutating the caller's forecast dict after record must not change the
    ledger's stored entry. The ledger owns its own snapshot."""
    ledger = ForecastLedger()
    forecast: dict[ReturnBucket, float] = _uniform()
    ledger.record("sig", forecast, "zero_to_plus_5")
    # Caller mutates their dict to a degenerate forecast on a different bucket.
    forecast["below_minus_5"] = 0.99
    forecast["zero_to_plus_5"] = 0.0025
    # Ledger reliability should still reflect the uniform claim, not the mutated
    # one. With one entry, mean_claim across all (claim, outcome) pairs is 0.2.
    buckets = ledger.reliability_for_signal_class("sig", n_buckets=10)
    # All 5 (claim, outcome) pairs have claim=0.2; they land in the [0.2, 0.3) bucket.
    assert len(buckets) == 1
    assert abs(buckets[0].mean_claim - 0.2) < 1e-9


# ---------------------------------------------------------------------------
# reliability_for_signal_class.
# ---------------------------------------------------------------------------


def test_reliability_unknown_signal_class_returns_empty_list() -> None:
    """A signal class never recorded under returns []."""
    ledger = ForecastLedger()
    ledger.record("sig_a", _uniform(), "zero_to_plus_5")
    assert ledger.reliability_for_signal_class("sig_unknown") == []


def test_reliability_isolates_signal_classes() -> None:
    """Entries under one signal class must not contribute to another's
    reliability. Mix uniform claims for sig_a and degenerate-correct claims
    for sig_b; check that sig_a's reliability ignores sig_b's entries."""
    ledger = ForecastLedger()
    # 20 uniform forecasts under sig_a, realized buckets vary
    realized_seq: list[ReturnBucket] = [
        "zero_to_plus_5",
        "below_minus_5",
        "above_plus_10",
        "plus_5_to_plus_10",
        "minus_5_to_0",
    ] * 4
    for r in realized_seq:
        ledger.record("sig_a", _uniform(), r)
    # 10 degenerate-correct forecasts under sig_b (claim 1.0 on the realized bucket)
    for r in realized_seq[:10]:
        ledger.record("sig_b", _degenerate_on(r), r)

    sig_a = ledger.reliability_for_signal_class("sig_a", n_buckets=10)
    # sig_a: all claims are 0.2. Across 20 records x 5 buckets = 100 (claim, outcome)
    # pairs. The realized bucket lands in each of the 5 buckets exactly 4 times,
    # so each (claim, outcome) pair contributes 1 to outcomes 4/20 of the time
    # (each bucket realized 4 out of 20 episodes). Observed rate = 0.2 exactly.
    assert len(sig_a) == 1
    assert abs(sig_a[0].mean_claim - 0.2) < 1e-9
    assert abs(sig_a[0].observed_rate - 0.2) < 1e-9
    assert sig_a[0].count == 100  # 20 records x 5 buckets

    sig_b = ledger.reliability_for_signal_class("sig_b", n_buckets=10)
    # sig_b: each record has one claim ≈ 1.0 on the correct bucket and 4 claims
    # near 0.0 on the others. So a high-claim bucket [0.9, 1.0] populated with
    # observed_rate ≈ 1.0 and a low-claim bucket [0.0, 0.1) populated with
    # observed_rate ≈ 0.0. Both on the diagonal — degenerate-correct is perfectly
    # calibrated by construction.
    high = next(b for b in sig_b if b.lo >= 0.9)
    low = next(b for b in sig_b if b.hi <= 0.1)
    assert abs(high.observed_rate - 1.0) < 1e-6
    assert abs(low.observed_rate - 0.0) < 1e-6


def test_reliability_perfectly_calibrated_stream_sits_on_diagonal() -> None:
    """A stream where the forecast equals the empirical realized-bucket
    distribution should produce reliability points where mean_claim ≈
    observed_rate in each bucket. Generate 50 forecasts that all claim
    P=0.4 on `zero_to_plus_5` and P=0.6 on `above_plus_10`; realize
    `zero_to_plus_5` 40% of the time and `above_plus_10` 60% of the
    time."""
    ledger = ForecastLedger()
    forecast: dict[ReturnBucket, float] = {b: 0.0 for b in RETURN_BUCKETS}
    forecast["zero_to_plus_5"] = 0.4
    forecast["above_plus_10"] = 0.6
    # 50 records: 20 realize zero_to_plus_5, 30 realize above_plus_10
    for _ in range(20):
        ledger.record("sig", forecast, "zero_to_plus_5")
    for _ in range(30):
        ledger.record("sig", forecast, "above_plus_10")
    buckets = ledger.reliability_for_signal_class("sig", n_buckets=10)

    # Three populated buckets:
    #   - claim 0.0 → bucket [0.0, 0.1); 50 records x 3 zero-claim buckets = 150
    #     pairs, outcome=0 on every pair (the zero-claim buckets never realize)
    #     → observed_rate = 0.0. On the diagonal.
    #   - claim 0.4 → bucket [0.4, 0.5); 50 pairs total, outcome=1 in the
    #     20 records where zero_to_plus_5 realized = 20/50 = 0.4
    #   - claim 0.6 → bucket [0.6, 0.7); 50 pairs total, outcome=1 in the
    #     30 records where above_plus_10 realized = 30/50 = 0.6
    # All three perfectly on the diagonal.
    pop = [b for b in buckets if b.count >= 50]
    assert len(pop) == 3
    for b in pop:
        gap = abs(b.mean_claim - b.observed_rate)
        assert gap < 1e-9, (
            f"Calibrated stream bucket [{b.lo:.2f}, {b.hi:.2f}) has gap {gap}; expected gap = 0"
        )


def test_reliability_overconfident_stream_shows_high_claim_gap() -> None:
    """A confidently-wrong stream — claims P≈1.0 on a bucket but it only
    realizes a third of the time — should produce a large (claim - observed)
    gap in the high-claim bucket."""
    ledger = ForecastLedger()
    confident_on_above_plus_10 = _degenerate_on("above_plus_10")
    realized_seq: list[ReturnBucket] = [
        "above_plus_10",
        "zero_to_plus_5",
        "below_minus_5",
    ] * 30  # 90 records, above_plus_10 happens 30 times (1/3)
    for r in realized_seq:
        ledger.record("sig", confident_on_above_plus_10, r)
    buckets = ledger.reliability_for_signal_class("sig", n_buckets=10)
    # High-claim bucket [0.9, 1.0]: 90 pairs (one per record), observed_rate
    # = 30/90 = 1/3. Gap = ~1.0 - 1/3 ≈ 0.667.
    high = next(b for b in buckets if b.lo >= 0.9)
    assert high.count == 90
    assert high.mean_claim > 0.99
    assert abs(high.observed_rate - 1.0 / 3.0) < 1e-9
    assert high.mean_claim - high.observed_rate > 0.5  # signature of overconfidence


def test_reliability_underconfident_stream_shows_low_claim_gap() -> None:
    """Same confidently-wrong stream — the low-claim bucket [0.0, 0.1) is
    populated by the four non-target buckets with claim ≈ 0. The observed
    rate of those pairs is the average frequency of those buckets, ~1/6
    each (two of the three realized buckets are non-target; with 4 low-claim
    pairs per record, the non-realized share is high)."""
    ledger = ForecastLedger()
    confident_on_above_plus_10 = _degenerate_on("above_plus_10")
    realized_seq: list[ReturnBucket] = [
        "above_plus_10",
        "zero_to_plus_5",
        "below_minus_5",
    ] * 30  # 90 records
    for r in realized_seq:
        ledger.record("sig", confident_on_above_plus_10, r)
    buckets = ledger.reliability_for_signal_class("sig", n_buckets=10)
    # Low-claim bucket [0.0, 0.1): 4 (claim, outcome) pairs per record x 90
    # records = 360 pairs. Of those, outcome=1 iff the realized bucket equals
    # the specific non-target bucket. Across 4 non-target buckets and 90
    # records where 2/3 of records have a non-target realized, the total
    # outcome count = 60 (the two non-target realized buckets each contribute
    # 30). So observed_rate = 60/360 = 1/6.
    low = next(b for b in buckets if b.hi <= 0.1)
    assert low.count == 360
    assert low.mean_claim < 0.01
    assert abs(low.observed_rate - 1.0 / 6.0) < 1e-9
    assert low.observed_rate - low.mean_claim > 0.1  # signature of underconfidence


# ---------------------------------------------------------------------------
# n_buckets parameter — propagates through to reliability_buckets.
# ---------------------------------------------------------------------------


def test_reliability_respects_n_buckets_parameter() -> None:
    """Default n_buckets=10; passing a different value changes bucket widths."""
    ledger = ForecastLedger()
    forecast: dict[ReturnBucket, float] = {b: 1.0 / len(RETURN_BUCKETS) for b in RETURN_BUCKETS}
    for _ in range(10):
        ledger.record("sig", forecast, "zero_to_plus_5")
    # n_buckets=10 → claim 0.2 lands in [0.2, 0.3) → bucket lo=0.2
    b10 = ledger.reliability_for_signal_class("sig", n_buckets=10)
    assert len(b10) == 1
    assert b10[0].lo == 0.2
    # n_buckets=5 → claim 0.2 lands in [0.2, 0.4) → bucket lo=0.2
    b5 = ledger.reliability_for_signal_class("sig", n_buckets=5)
    assert len(b5) == 1
    assert b5[0].lo == 0.2
    assert b5[0].hi == 0.4


def test_reliability_buckets_n_buckets_lt_2_raises() -> None:
    """n_buckets < 2 is rejected by the underlying reliability_buckets call."""
    ledger = ForecastLedger()
    ledger.record("sig", _uniform(), "zero_to_plus_5")
    with pytest.raises(ValueError, match="n_buckets"):
        ledger.reliability_for_signal_class("sig", n_buckets=1)
