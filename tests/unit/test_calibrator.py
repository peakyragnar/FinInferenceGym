"""Unit tests for the calibration shrinkage function (Stone 11c).

Covers:
  - **Identity properties**: empty Ledger and unknown signal class both
    return the raw forecast unchanged.
  - **Renormalization invariant**: output always sums to 1.
  - **Fixed-point property**: a raw forecast that already matches the
    Ledger's empirical bin-by-bin returns unchanged.
  - **Formula verification**: hand-computed cases at specific (n,
    empirical, raw, k) values match the shrunk output.
  - **Sparse vs dense (the central property of shrinkage)**: with the
    same raw forecast and empirical, more samples pull the shrunk value
    closer to empirical; fewer samples leave it closer to raw.
  - **Signal class isolation**: entries under one signal class do not
    affect shrinkage of a different signal class.
  - **prior_strength tuning**: smaller `k` is more aggressive; larger `k`
    is more conservative.
  - **Validation**: `prior_strength <= 0` raises.

End-to-end Cluster B behavior against the full toy + Ledger pipeline
is locked in by the Cluster B integration test (when 11d-c lands).
"""

from __future__ import annotations

import pytest

from fingym.action.calibrator import DEFAULT_PRIOR_STRENGTH, shrink
from fingym.ledger.forecast_ledger import ForecastLedger
from fingym.toys.synthetic_market import RETURN_BUCKETS, ReturnBucket

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _uniform() -> dict[ReturnBucket, float]:
    return {b: 1.0 / len(RETURN_BUCKETS) for b in RETURN_BUCKETS}


def _confident_on(target: ReturnBucket, confidence: float = 0.95) -> dict[ReturnBucket, float]:
    other_count = len(RETURN_BUCKETS) - 1
    other = (1.0 - confidence) / other_count
    return {b: (confidence if b == target else other) for b in RETURN_BUCKETS}


# ---------------------------------------------------------------------------
# Identity properties — empty Ledger and unknown signal class.
# ---------------------------------------------------------------------------


def test_empty_ledger_returns_raw_forecast_unchanged() -> None:
    """No entries anywhere → shrinkage is identity for every bucket."""
    ledger = ForecastLedger()
    raw = _confident_on("below_minus_5", confidence=0.95)
    calibrated = shrink(raw, "new_signal_class", ledger)
    for b in RETURN_BUCKETS:
        assert calibrated[b] == pytest.approx(raw[b])


def test_unknown_signal_class_returns_raw_forecast_unchanged() -> None:
    """Records under OTHER signal classes do not affect this signal class."""
    ledger = ForecastLedger()
    for _ in range(100):
        ledger.record("other_sig", _uniform(), "below_minus_5")
    raw = _confident_on("below_minus_5", confidence=0.95)
    calibrated = shrink(raw, "untracked_sig", ledger)
    for b in RETURN_BUCKETS:
        assert calibrated[b] == pytest.approx(raw[b])


def test_claim_in_unpopulated_bin_passes_through() -> None:
    """If a raw claim lands in a Ledger bin with no entries, that bucket
    passes through identity. Construct a Ledger where only the [0.9, 1.0]
    and [0.0, 0.1] bins are populated (via ConfidentAgent's 0.95/0.0125
    claims), then shrink a raw forecast where one bucket's claim is 0.5
    (in the empty [0.5, 0.6) bin)."""
    ledger = ForecastLedger()
    for _ in range(10):
        ledger.record(
            "conf_sig",
            _confident_on("below_minus_5", confidence=0.95),
            "below_minus_5",
        )
    # The Ledger's populated bins are [0.0, 0.1) (4*10=40 pairs at 0.0125
    # claim) and [0.9, 1.0] (10 pairs at 0.95 claim). Other bins empty.
    raw: dict[ReturnBucket, float] = {
        "below_minus_5": 0.5,  # bin [0.5, 0.6) — unpopulated, identity
        "minus_5_to_0": 0.5,  # bin [0.5, 0.6) — unpopulated, identity
        "zero_to_plus_5": 0.0,  # bin [0.0, 0.1) — populated, will shrink
        "plus_5_to_plus_10": 0.0,  # bin [0.0, 0.1) — populated, will shrink
        "above_plus_10": 0.0,  # bin [0.0, 0.1) — populated, will shrink
    }
    # Pre-renorm: the two [0.5, 0.6) buckets pass through at 0.5; the three
    # [0.0, 0.1) buckets shrink toward the empirical for that bin.
    calibrated = shrink(raw, "conf_sig", ledger)
    # Sanity: the unpopulated-bin buckets retain their RELATIVE size — both
    # were 0.5 raw, so both are still equal post-renorm. The renorm is the
    # only difference between pre and post.
    assert calibrated["below_minus_5"] == pytest.approx(calibrated["minus_5_to_0"])


# ---------------------------------------------------------------------------
# Renormalization invariant.
# ---------------------------------------------------------------------------


def test_output_sums_to_1() -> None:
    """Shrunk distribution always sums to 1, regardless of Ledger state."""
    ledger = ForecastLedger()
    for _ in range(50):
        ledger.record("sig", _confident_on("above_plus_10", confidence=0.8), "zero_to_plus_5")
    raw = _confident_on("below_minus_5", confidence=0.7)
    calibrated = shrink(raw, "sig", ledger)
    assert sum(calibrated.values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Fixed-point property.
# ---------------------------------------------------------------------------


def test_perfectly_calibrated_raw_is_fixed_point() -> None:
    """If the raw forecast already matches the Ledger empirical bin-by-bin,
    shrinkage returns the raw unchanged (modulo renormalization, which is
    the identity when the distribution already sums to 1).

    Construct: agent always claims 0.4 on `zero_to_plus_5` and 0.6 on
    `above_plus_10`. Realize `zero_to_plus_5` 40% of the time and
    `above_plus_10` 60% of the time. The Ledger's [0.4, 0.5) bin has
    empirical 0.4; the [0.6, 0.7) bin has empirical 0.6.
    """
    ledger = ForecastLedger()
    raw: dict[ReturnBucket, float] = {b: 0.0 for b in RETURN_BUCKETS}
    raw["zero_to_plus_5"] = 0.4
    raw["above_plus_10"] = 0.6
    for _ in range(40):
        ledger.record("sig", raw, "zero_to_plus_5")
    for _ in range(60):
        ledger.record("sig", raw, "above_plus_10")
    calibrated = shrink(raw, "sig", ledger)
    for b in RETURN_BUCKETS:
        assert calibrated[b] == pytest.approx(raw[b], abs=1e-9)


# ---------------------------------------------------------------------------
# Formula verification — hand-computed.
# ---------------------------------------------------------------------------


def test_formula_matches_hand_computed_value() -> None:
    """Construct a Ledger with known (n, empirical) in a specific bin, then
    verify the shrunk output matches the formula exactly.

    Setup: 100 records under signal `s`. Each record claims [0.85, 0.0375,
    0.0375, 0.0375, 0.0375] (target=below_minus_5, sums to 1); realized is
    always below_minus_5. So:
      - bin [0.8, 0.9): n=100, all 100 outcomes=1 → empirical=1.0
      - bin [0.0, 0.1): n=400, all 400 outcomes=0 → empirical=0.0

    Apply shrinkage at k=20 to the same forecast:
      - target (raw=0.85, bin [0.8, 0.9)): shrunk = (100*1.0 + 20*0.85)/120
        = 117/120 = 0.975
      - others (raw=0.0375, bin [0.0, 0.1)): shrunk = (400*0.0 + 20*0.0375)/420
        = 0.75/420 = 0.001785714...

    Sum pre-renorm: 0.975 + 4*0.001785714 = 0.982142857
    Post-renorm:
      - target = 0.975 / 0.982142857 = 0.99272727...
      - others = 0.001785714 / 0.982142857 = 0.00181818...
    """
    ledger = ForecastLedger()
    raw: dict[ReturnBucket, float] = {b: 0.0375 for b in RETURN_BUCKETS}
    raw["below_minus_5"] = 0.85
    for _ in range(100):
        ledger.record("s", raw, "below_minus_5")

    calibrated = shrink(raw, "s", ledger, prior_strength=20.0)
    # Expected post-renorm values
    target_pre = (100 * 1.0 + 20 * 0.85) / 120
    others_pre = (400 * 0.0 + 20 * 0.0375) / 420
    total_pre = target_pre + 4 * others_pre
    expected_target = target_pre / total_pre
    expected_others = others_pre / total_pre

    assert calibrated["below_minus_5"] == pytest.approx(expected_target, abs=1e-12)
    for b in RETURN_BUCKETS:
        if b == "below_minus_5":
            continue
        assert calibrated[b] == pytest.approx(expected_others, abs=1e-12)


# ---------------------------------------------------------------------------
# Sparse vs dense — the central property of shrinkage.
# ---------------------------------------------------------------------------


def test_more_samples_pull_shrunk_closer_to_empirical() -> None:
    """Same raw, same empirical pattern, but different sample sizes. The
    Ledger with more samples should produce shrinkage that lands closer to
    empirical than the Ledger with fewer samples.

    Construct: ConfidentAgent claims 0.95 on `below_minus_5` and 0.0125
    elsewhere; realized is always `zero_to_plus_5` (never the claimed
    bucket). Empirical in [0.9, 1.0]: 0.0 (target never realizes).
    """
    forecast = _confident_on("below_minus_5", confidence=0.95)

    sparse = ForecastLedger()
    for _ in range(5):
        sparse.record("sig", forecast, "zero_to_plus_5")

    dense = ForecastLedger()
    for _ in range(500):
        dense.record("sig", forecast, "zero_to_plus_5")

    sparse_cal = shrink(forecast, "sig", sparse)
    dense_cal = shrink(forecast, "sig", dense)

    # The raw 0.95 on below_minus_5 should be pulled further toward the
    # empirical 0.0 by the dense Ledger than by the sparse one.
    raw_target = 0.95
    sparse_distance_from_empirical = abs(sparse_cal["below_minus_5"] - 0.0)
    dense_distance_from_empirical = abs(dense_cal["below_minus_5"] - 0.0)
    assert dense_distance_from_empirical < sparse_distance_from_empirical, (
        f"Dense Ledger should shrink closer to empirical 0.0; "
        f"got sparse={sparse_cal['below_minus_5']:.4f}, "
        f"dense={dense_cal['below_minus_5']:.4f}, raw={raw_target}"
    )


# ---------------------------------------------------------------------------
# Signal class isolation.
# ---------------------------------------------------------------------------


def test_signal_class_isolation() -> None:
    """Build a Ledger with two signal classes that would prescribe DIFFERENT
    shrinkage on the same raw forecast. Verify that shrinking under each
    signal class produces a different calibrated output — proving the
    calibrator looks up by signal_class_id, not globally."""
    ledger = ForecastLedger()
    forecast = _confident_on("below_minus_5", confidence=0.95)
    # Under sig_a: target NEVER realizes (empirical for high-claim bin = 0)
    for _ in range(100):
        ledger.record("sig_a", forecast, "zero_to_plus_5")
    # Under sig_b: target ALWAYS realizes (empirical for high-claim bin = 1)
    for _ in range(100):
        ledger.record("sig_b", forecast, "below_minus_5")

    cal_a = shrink(forecast, "sig_a", ledger)
    cal_b = shrink(forecast, "sig_b", ledger)

    # sig_a pulls below_minus_5 way down (empirical 0); sig_b leaves it high
    # (empirical 1). The two calibrated values must differ markedly.
    assert cal_a["below_minus_5"] < 0.5, (
        f"Under sig_a (empirical 0), 0.95 raw should shrink well below 0.5; "
        f"got {cal_a['below_minus_5']:.3f}"
    )
    assert cal_b["below_minus_5"] > 0.8, (
        f"Under sig_b (empirical 1), 0.95 raw should stay near 0.95; "
        f"got {cal_b['below_minus_5']:.3f}"
    )


# ---------------------------------------------------------------------------
# prior_strength tuning.
# ---------------------------------------------------------------------------


def test_smaller_prior_strength_is_more_aggressive() -> None:
    """Same raw, same Ledger. Smaller `prior_strength` (k) gives the Ledger
    more weight → shrinks closer to empirical. Larger k gives raw more
    weight → leaves the shrunk value closer to raw."""
    ledger = ForecastLedger()
    forecast = _confident_on("below_minus_5", confidence=0.95)
    for _ in range(20):  # sparse-ish; k vs n contest is meaningful
        ledger.record("sig", forecast, "zero_to_plus_5")

    cal_aggressive = shrink(forecast, "sig", ledger, prior_strength=5.0)
    cal_default = shrink(forecast, "sig", ledger, prior_strength=20.0)
    cal_conservative = shrink(forecast, "sig", ledger, prior_strength=100.0)

    # Empirical for [0.9, 1.0] is 0.0; raw is 0.95. Lower k pulls below_minus_5
    # closer to 0; higher k leaves it closer to 0.95.
    assert (
        cal_aggressive["below_minus_5"]
        < cal_default["below_minus_5"]
        < cal_conservative["below_minus_5"]
    ), (
        f"Aggressive k=5: {cal_aggressive['below_minus_5']:.3f}; "
        f"default k=20: {cal_default['below_minus_5']:.3f}; "
        f"conservative k=100: {cal_conservative['below_minus_5']:.3f}"
    )


def test_default_prior_strength_is_documented() -> None:
    """The module exposes DEFAULT_PRIOR_STRENGTH for operator visibility."""
    assert DEFAULT_PRIOR_STRENGTH == 20.0


# ---------------------------------------------------------------------------
# Validation.
# ---------------------------------------------------------------------------


def test_zero_prior_strength_raises() -> None:
    """prior_strength=0 is undefined under the formula (would divide n+0
    by 0+0 = 0 when n=0). Reject at the boundary."""
    ledger = ForecastLedger()
    with pytest.raises(ValueError, match="prior_strength"):
        shrink(_uniform(), "sig", ledger, prior_strength=0.0)


def test_negative_prior_strength_raises() -> None:
    """prior_strength must be strictly positive."""
    ledger = ForecastLedger()
    with pytest.raises(ValueError, match="prior_strength"):
        shrink(_uniform(), "sig", ledger, prior_strength=-1.0)


# ---------------------------------------------------------------------------
# Three-agent table — concrete behavior matching the PYRAMID summary.
# ---------------------------------------------------------------------------


def test_confident_agent_high_claim_gets_crushed() -> None:
    """ConfidentAgent's 0.95 on `below_minus_5` should be pulled well below
    0.5 after 100 episodes of Ledger history under a realistic toy run
    where the target bucket only realizes ~25% of the time.

    Construct a Ledger that mimics the 100-episode toy stats: 27 of 100
    records have target realized; 73 have a different bucket realized.
    Empirical for the [0.9, 1.0] bin = 27/100 = 0.27.
    """
    ledger = ForecastLedger()
    confident_forecast = _confident_on("below_minus_5", confidence=0.95)
    # 27 records where target realizes; 73 where zero_to_plus_5 does.
    for _ in range(27):
        ledger.record("confident_static", confident_forecast, "below_minus_5")
    for _ in range(73):
        ledger.record("confident_static", confident_forecast, "zero_to_plus_5")

    calibrated = shrink(confident_forecast, "confident_static", ledger)
    # Raw 0.95 → expected to shrink toward empirical 0.27. The PYRAMID
    # table predicts ~0.38 pre-renorm; post-renorm should be in the
    # vicinity. Assert it's well below the raw 0.95.
    assert calibrated["below_minus_5"] < 0.6, (
        f"ConfidentAgent's 0.95 should shrink well below 0.6 "
        f"(saw {calibrated['below_minus_5']:.3f}; raw=0.95, empirical=0.27)"
    )


def test_uniform_agent_passes_through_when_empirical_matches_raw() -> None:
    """UniformAgent always claims 0.2 per bucket; by symmetry, empirical for
    [0.2, 0.3) is also 0.2 (each bucket realizes 1/5 of the time on average).
    Shrinkage should return ~0.2 per bucket — unchanged within renorm noise."""
    ledger = ForecastLedger()
    uniform_forecast = _uniform()
    # 20 records realizing each of the 5 buckets → uniform realized
    # distribution, so empirical for [0.2, 0.3) = 0.2.
    realized_seq: list[ReturnBucket] = list(RETURN_BUCKETS) * 20  # 100 records
    for r in realized_seq:
        ledger.record("uniform_static", uniform_forecast, r)

    calibrated = shrink(uniform_forecast, "uniform_static", ledger)
    for b in RETURN_BUCKETS:
        assert calibrated[b] == pytest.approx(0.2, abs=1e-9), (
            f"UniformAgent bucket {b}: expected ~0.2, got {calibrated[b]:.4f}"
        )
