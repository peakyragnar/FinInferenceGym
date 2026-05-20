"""RealMarketStateBaseline — N-dimensional Bayesian Ledger over real
headline observables.

Parallel to the toy MarketStateBaseline (3-dim, fixed series), this
class conditions on N FRED-series buckets. Same structural pattern:
empirical conditional distribution over realized-return buckets, with
uniform-prior fallback for unseen cells.

Bucket assignment is two-bucket median split per series:
  - low  := value < median
  - high := value >= median

Median cutpoints are computed from historical data once (during training)
and held as a frozen config so inference is deterministic per (cutpoint,
value).

Design choice: 2 buckets per series (vs 3) yields 2^7 = 128 cells. With
~17,000 historical (ticker, trading-day) observations across our 7-name
test universe, that's ~133 obs/cell on average. Robust learning per cell.
Documented in real_data_ingest.md Stage 1 wiring step.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from fingym.data.queries.equity_returns import RETURN_BUCKETS, ReturnBucket

RealObservableBucket = Literal["low", "high"]
REAL_BUCKETS: tuple[RealObservableBucket, ...] = ("low", "high")

# Ordered key — tuple of bucket labels in BASELINE_SERIES order.
RealStateKey = tuple[RealObservableBucket, ...]

REAL_BASELINE_AGENT_ID = "market_state_baseline_real"


def bucket_value(value: Decimal, cutpoint: Decimal) -> RealObservableBucket:
    """Median split: value < cutpoint → low; value >= cutpoint → high."""
    return "low" if value < cutpoint else "high"


def state_key_from_values(
    values: dict[str, Decimal],
    cutpoints: dict[str, Decimal],
    series_order: tuple[str, ...],
) -> RealStateKey | None:
    """Build the Ledger key from a macro state dict.

    Returns None if any series in series_order is missing from values
    (caller decides whether to skip or use defaults). The series_order
    parameter is the canonical ordering (e.g., BASELINE_SERIES from the
    headline_observables query module).
    """
    out: list[RealObservableBucket] = []
    for series_id in series_order:
        if series_id not in values:
            return None
        if series_id not in cutpoints:
            return None
        out.append(bucket_value(values[series_id], cutpoints[series_id]))
    return tuple(out)


def _uniform_forecast() -> dict[ReturnBucket, float]:
    p = 1.0 / len(RETURN_BUCKETS)
    return dict.fromkeys(RETURN_BUCKETS, p)


@dataclass
class RealMarketStateBaseline:
    """Bayesian Ledger over N-tuple bucket combinations.

    Configured at construction with:
      - series_order: canonical ordering of FRED series_ids
      - cutpoints: median per series_id, used to bucket numeric values

    The class is otherwise identical in shape to the toy MarketStateBaseline.
    """

    series_order: tuple[str, ...]
    cutpoints: dict[str, Decimal]
    cell_counts: dict[RealStateKey, dict[ReturnBucket, int]] = field(
        default_factory=lambda: defaultdict(lambda: dict.fromkeys(RETURN_BUCKETS, 0))
    )

    def record(self, macro_values: dict[str, Decimal], realized: ReturnBucket) -> bool:
        """Update the cell at the macro state with one observation.

        Returns True if recorded, False if the macro state is incomplete
        (some required series missing)."""
        key = state_key_from_values(macro_values, self.cutpoints, self.series_order)
        if key is None:
            return False
        if key not in self.cell_counts:
            self.cell_counts[key] = dict.fromkeys(RETURN_BUCKETS, 0)
        self.cell_counts[key][realized] += 1
        return True

    def forecast(self, macro_values: dict[str, Decimal]) -> dict[ReturnBucket, float]:
        """Return the empirical distribution at the macro state, uniform
        fallback if the cell is empty or the state is incomplete."""
        key = state_key_from_values(macro_values, self.cutpoints, self.series_order)
        if key is None:
            return _uniform_forecast()
        counts = self.cell_counts.get(key)
        if counts is None:
            return _uniform_forecast()
        total = sum(counts.values())
        if total == 0:
            return _uniform_forecast()
        return {bucket: counts[bucket] / total for bucket in RETURN_BUCKETS}

    def cell_sample_size(self, macro_values: dict[str, Decimal]) -> int:
        key = state_key_from_values(macro_values, self.cutpoints, self.series_order)
        if key is None:
            return 0
        counts = self.cell_counts.get(key)
        if counts is None:
            return 0
        return sum(counts.values())

    def cells_populated(self) -> int:
        return sum(1 for counts in self.cell_counts.values() if sum(counts.values()) > 0)

    def total_observations(self) -> int:
        return sum(sum(counts.values()) for counts in self.cell_counts.values())


__all__ = [
    "REAL_BASELINE_AGENT_ID",
    "REAL_BUCKETS",
    "RealMarketStateBaseline",
    "RealObservableBucket",
    "RealStateKey",
    "bucket_value",
    "state_key_from_values",
]
