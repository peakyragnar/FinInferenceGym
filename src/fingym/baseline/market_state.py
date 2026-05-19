"""MarketStateBaseline — Bayesian Ledger over (rate, vol, fx) buckets.

The information-poor null hypothesis (PYRAMID Stone 11e, Cluster I). The
Baseline learns the empirical conditional distribution

    P(realized return bucket | rate_bucket, vol_bucket, fx_bucket)

from observed (HeadlineObservables, realized_bucket) pairs, and emits
that distribution as its forecast at decision time.

Architectural symmetry with Cluster A's Forecast Ledger: the Baseline IS
a Forecast Ledger, keyed on observables instead of on a model-chosen
signal_class_id. The same simple Bayesian smoothing applies: empty
buckets fall back to a uniform prior over return buckets so the Baseline
makes a defensible default forecast even on observable combinations it
hasn't seen yet.

The Baseline runs through the same Action Engine + structured cost
model + realized_edge as the AI; its rows land on the Scoreboard under
`agent_id="market_state_baseline"`. The Scoreboard's
`incremental_AI_edge` helper computes attribution.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from fingym.toys.synthetic_market import (
    RETURN_BUCKETS,
    HeadlineObservables,
    ObservableBucket,
    ReturnBucket,
)

# Agent ID the Baseline uses on its Scoreboard rows. Constant so the
# Scoreboard helper can compute incremental_AI_edge by slicing on it.
BASELINE_AGENT_ID: str = "market_state_baseline"


# Type alias for the Baseline's Ledger key: a tuple of (rate, vol, fx) buckets.
ObservableTuple = tuple[ObservableBucket, ObservableBucket, ObservableBucket]


def _observable_tuple(obs: HeadlineObservables) -> ObservableTuple:
    return (obs.rate, obs.vol, obs.fx)


def _uniform_forecast() -> dict[ReturnBucket, float]:
    """Uniform prior over the five return buckets. Returned when the
    Baseline has no observations under the queried (rate, vol, fx) cell.
    """
    p = 1.0 / len(RETURN_BUCKETS)
    return dict.fromkeys(RETURN_BUCKETS, p)


@dataclass
class MarketStateBaseline:
    """Bayesian Ledger over (rate, vol, fx) bucket combinations.

    Internal state is a counts table: cell_counts[(rate, vol, fx)][realized_bucket]
    accumulates from observed records. Forecasts are read as the
    normalized counts (with uniform fallback for unseen cells).

    Per-cell sample sizes are typically modest in the toy (27 cells, 100
    episodes -> ~4 observations per cell), so we smooth empty cells to
    the uniform prior rather than e.g. Beta(1,1) Bayesian smoothing — the
    point in toy mode is the architectural pattern, not the model's
    sophistication.
    """

    cell_counts: dict[ObservableTuple, dict[ReturnBucket, int]] = field(
        default_factory=lambda: defaultdict(lambda: dict.fromkeys(RETURN_BUCKETS, 0))
    )

    def record(self, observables: HeadlineObservables, realized: ReturnBucket) -> None:
        """Update the cell at (rate, vol, fx) with one observation."""
        key = _observable_tuple(observables)
        if key not in self.cell_counts:
            self.cell_counts[key] = dict.fromkeys(RETURN_BUCKETS, 0)
        self.cell_counts[key][realized] += 1

    def forecast(self, observables: HeadlineObservables) -> dict[ReturnBucket, float]:
        """Return the empirical distribution at the queried cell.

        Empty cell (no observations yet under this (rate, vol, fx)
        combination) falls back to uniform over the five return buckets.
        """
        key = _observable_tuple(observables)
        counts = self.cell_counts.get(key)
        if counts is None:
            return _uniform_forecast()
        total = sum(counts.values())
        if total == 0:
            return _uniform_forecast()
        return {bucket: counts[bucket] / total for bucket in RETURN_BUCKETS}

    def cell_sample_size(self, observables: HeadlineObservables) -> int:
        """Number of observations under (rate, vol, fx). For audit /
        confidence diagnostics."""
        counts = self.cell_counts.get(_observable_tuple(observables))
        if counts is None:
            return 0
        return sum(counts.values())


__all__ = ["BASELINE_AGENT_ID", "MarketStateBaseline", "ObservableTuple"]
