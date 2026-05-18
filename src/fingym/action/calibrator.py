"""calibrator.py — calibration shrinkage (Phase 1 NEW Cluster B, Stone 11c).

Rewrites an agent's raw forecast toward the empirical per-signal-class
reliability tracked by the Forecast Ledger, producing `F_AI_calibrated`.
This is the verifier-side derivation that the Tradable-Edge Action Engine
(Stone 11d) consumes.

Formula (per PYRAMID Stone 11c distilled summary):

    shrunk[bucket] = (n * empirical + k * raw) / (n + k)

  - `n` = sample size of the Ledger claim-bin matching the raw claim
  - `empirical` = observed truth-rate in that Ledger bin
  - `k` = prior_strength (operator-tunable pseudo-count weight on the raw)
  - `raw` = the agent's current claim for this return bucket

Applied bin-by-bin to each of the N return buckets in the forecast; the
distribution is then renormalized to sum to 1.

Properties locked in:
  - Empty Ledger = identity (no entries → raw forecast passes through).
  - Sparse Ledger = gentle (low `n` → low weight on empirical).
  - Dense Ledger = aggressive (high `n` → empirical effectively overwrites).
  - Claims falling in unpopulated Ledger bins pass through unchanged.

Public surface:
  - `DEFAULT_PRIOR_STRENGTH` — module-level constant; toy MVP default.
  - `shrink(raw_forecast, signal_class_id, ledger, prior_strength)` —
    returns `F_AI_calibrated` as a `dict[ReturnBucket, float]`.
"""

from __future__ import annotations

from fingym.evaluator.scoring import ReliabilityBucket
from fingym.ledger.forecast_ledger import ForecastLedger, ForecastOverBuckets
from fingym.toys.synthetic_market import RETURN_BUCKETS, ReturnBucket

DEFAULT_PRIOR_STRENGTH: float = 20.0
"""Default pseudo-count weight on the raw forecast (operator-tunable).

`prior_strength = 20` means "treat the agent's raw claim as worth 20
pseudo-observations of history." The Ledger overtakes the raw claim once
it has ~20 entries in the matching bin. Smaller `k` is more aggressive
(empirical overtakes raw faster); larger `k` is more conservative.

Belongs in the operator-tunable parameter set, not in the architectural
commitments. Per-signal-class tuning is reasonable as the system matures.
"""


def _find_bin(
    buckets: list[ReliabilityBucket],
    claim: float,
) -> ReliabilityBucket | None:
    """Find the Ledger reliability bin containing `claim`, or None if the
    claim falls in an unpopulated bin (or the Ledger has no entries for
    this signal class).

    Matches the bin-boundary rule used by `reliability_buckets`:
    `[lo, hi)` for non-last bins; `[lo, hi]` for the last bin (so a
    claim of exactly 1.0 lands in the top bin under the default 10-bin
    grid).
    """
    for b in buckets:
        if b.lo <= claim < b.hi:
            return b
        if b.hi == 1.0 and claim == 1.0:
            return b
    return None


def shrink(
    raw_forecast: ForecastOverBuckets,
    signal_class_id: str,
    ledger: ForecastLedger,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    n_buckets: int = 10,
) -> dict[ReturnBucket, float]:
    """Shrink raw_forecast toward per-signal-class Ledger reliability.

    For each return bucket `b` in `raw_forecast`:
      1. Look up the Ledger reliability bin whose `[lo, hi)` contains
         `raw_forecast[b]`. If no bin matches (empty Ledger, or claim
         falls in an unpopulated bin), pass `raw_forecast[b]` through
         unchanged for that bucket.
      2. Otherwise compute `(n * empirical + k * raw) / (n + k)`.
    After all return buckets are shrunk, renormalize the distribution
    to sum to 1 and return the result.

    Raises `ValueError` if `prior_strength <= 0` (the formula is
    undefined at `k <= 0`) or if the shrunk distribution sums to zero
    or less (which can only happen on a malformed raw forecast).
    """
    if prior_strength <= 0:
        raise ValueError(
            f"prior_strength must be > 0; got {prior_strength}. "
            "k <= 0 is undefined under the shrinkage formula."
        )

    reliability = ledger.reliability_for_signal_class(signal_class_id, n_buckets=n_buckets)

    shrunk_raw: dict[ReturnBucket, float] = {}
    for return_bucket in RETURN_BUCKETS:
        raw = raw_forecast[return_bucket]
        match = _find_bin(reliability, raw)
        if match is None:
            shrunk_raw[return_bucket] = raw
        else:
            n = float(match.count)
            empirical = match.observed_rate
            shrunk_raw[return_bucket] = (n * empirical + prior_strength * raw) / (
                n + prior_strength
            )

    total = sum(shrunk_raw.values())
    if total <= 0.0:
        raise ValueError(
            f"Calibrated forecast sums to {total} <= 0; cannot renormalize. "
            "Likely the raw forecast was malformed (no positive mass)."
        )
    return {b: shrunk_raw[b] / total for b in RETURN_BUCKETS}


__all__ = ["DEFAULT_PRIOR_STRENGTH", "shrink"]
