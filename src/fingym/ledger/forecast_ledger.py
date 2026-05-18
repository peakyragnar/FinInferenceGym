"""Forecast Ledger MVP — Phase 1 NEW Cluster A, Stone 11b.

Append-only record of every (forecast, realized return) pair indexed by
signal class. Computes per-signal-class empirical reliability on demand
using the existing `reliability_buckets` primitive from
`fingym.evaluator.scoring`.

Schema is the same as the eventual Phase 2 NEW real-data version. The MVP
here proves the contract and the reliability-computation pattern in toy
mode before any vendor decisions are made. The Phase 2 NEW migration is
a backing-store swap (in-memory → Postgres view over `forecasts` +
`realized_returns`), not an API change.

Public surface:

  - `LedgerEntry` — frozen dataclass for one (signal_class_id, forecast,
    realized_bucket) tuple.
  - `ForecastLedger.record(...)` — append-only insert.
  - `ForecastLedger.reliability_for_signal_class(...)` — per-signal-class
    reliability buckets. This is the function Cluster B's calibration
    shrinkage will consume; the MVP surface matches the eventual real-data
    API.
  - `ForecastLedger.records_for_signal_class(...)`, `.all_signal_classes()`,
    `.total_records()` — audit / sanity accessors.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from fingym.evaluator.scoring import ReliabilityBucket, reliability_buckets
from fingym.toys.synthetic_market import RETURN_BUCKETS, ReturnBucket

type ForecastOverBuckets = Mapping[ReturnBucket, float]


@dataclass(frozen=True)
class LedgerEntry:
    """A single (forecast, realized bucket) pair, tagged by signal class.

    Append-only. The Ledger persists these tuples and computes reliability
    views on demand. Frozen by design — no mutation after record, keeps the
    audit story honest.
    """

    signal_class_id: str
    forecast: ForecastOverBuckets
    realized_bucket: ReturnBucket


@dataclass
class ForecastLedger:
    """In-memory Forecast Ledger MVP.

    Append-only store of (forecast, realized) pairs indexed by signal class.
    `reliability_for_signal_class` returns the empirical
    claimed-vs-observed-rate calibration data per signal class — the
    quantity Cluster B's calibration shrinkage shrinks the raw forecast
    toward.
    """

    _entries: list[LedgerEntry] = field(default_factory=list)

    def record(
        self,
        signal_class_id: str,
        forecast: ForecastOverBuckets,
        realized_bucket: ReturnBucket,
    ) -> None:
        """Append a (forecast, realized) pair tagged with signal_class_id.

        Forecast is copied defensively so the Ledger owns its own snapshot
        — caller mutations after the call cannot poison ledger history.
        Missing buckets are not allowed: forecast must define a probability
        for every member of RETURN_BUCKETS (the v5 forecast space).
        """
        snapshot: dict[ReturnBucket, float] = {b: forecast[b] for b in RETURN_BUCKETS}
        self._entries.append(
            LedgerEntry(
                signal_class_id=signal_class_id,
                forecast=snapshot,
                realized_bucket=realized_bucket,
            )
        )

    def reliability_for_signal_class(
        self,
        signal_class_id: str,
        n_buckets: int = 10,
    ) -> list[ReliabilityBucket]:
        """Per-signal-class empirical reliability over claimed-probability buckets.

        For every Ledger entry tagged with `signal_class_id`, expand the
        forecast into N_RETURN_BUCKETS (claim, outcome) pairs — one per
        return bucket, where `outcome = 1` iff that return bucket is the
        realized one. Pool all pairs across all entries for the signal
        class, then bucket the claims into `n_buckets` equal-width bins
        and return per-bin (mean_claim, observed_rate, count).

        This is the standard reliability-bucketing pattern from Stones 8
        / 18, applied per signal class.

        An unknown `signal_class_id` (no entries recorded) returns an empty
        list. Low-count bins are NOT filtered here — the caller (Cluster B's
        shrinkage) inspects `count` to decide how much to trust each bin.
        """
        claims: list[float] = []
        outcomes: list[int] = []
        for entry in self._entries:
            if entry.signal_class_id != signal_class_id:
                continue
            for bucket in RETURN_BUCKETS:
                claims.append(entry.forecast[bucket])
                outcomes.append(1 if bucket == entry.realized_bucket else 0)
        if not claims:
            return []
        return reliability_buckets(claims, outcomes, n_buckets=n_buckets)

    def records_for_signal_class(self, signal_class_id: str) -> int:
        """How many (forecast, realized) pairs we've recorded under this id."""
        return sum(1 for e in self._entries if e.signal_class_id == signal_class_id)

    def all_signal_classes(self) -> list[str]:
        """Distinct signal_class_ids seen, in first-seen order."""
        seen: list[str] = []
        seen_set: set[str] = set()
        for entry in self._entries:
            if entry.signal_class_id in seen_set:
                continue
            seen.append(entry.signal_class_id)
            seen_set.add(entry.signal_class_id)
        return seen

    def total_records(self) -> int:
        """Total number of ledger entries across all signal classes."""
        return len(self._entries)


__all__ = ["ForecastLedger", "ForecastOverBuckets", "LedgerEntry"]
