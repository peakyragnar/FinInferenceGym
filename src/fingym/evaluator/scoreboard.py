"""Scoreboard for the v5 toy (PYRAMID Stones 9, 10, 11, 11b, 11c, 11d, 14).

One row per `(Contract, horizon)` pair. Each row carries every scoring column
built so far in Phase 1 NEW:

  - Identity / metadata: agent_id, signal_class_id, horizon, decision_time
  - Cognition: forecast_distribution (raw), calibrated_forecast
  - Forward-looking (Stone 11d): calibrated_expected_return,
    calibrated_expected_utility, tradable_edge_score, kelly_fraction_applied,
    final_action
  - Backward-looking (Stones 6, 7, 14): realized_return, realized_bucket,
    brier, log_score, realized_edge

The scoreboard is the v5 reformulation of Stone 9's row schema: one row per
(decision-time, horizon) pair, with all columns populated at scoring time.

Aggregation pattern (Stone 9):
  - Filter by metadata (`filter_by_horizon`, `filter_by_signal_class`,
    `filter_by_agent`).
  - Compute column means on filtered subsets (`mean_brier`, `mean_log_score`,
    `mean_realized_edge`).

Append-only by convention; no row mutated in place after scoring.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from fingym.agents.contract import NoAction, TradeAction
from fingym.ledger.forecast_ledger import ForecastOverBuckets
from fingym.toys.synthetic_market import ReturnBucket


@dataclass(frozen=True)
class ScoreboardRow:
    """One row of the scoreboard: per-(Contract, horizon) scoring record.

    Frozen — append-only audit semantics. Once a row is written, it does
    not change. Aggregations read the rows; they never mutate them.
    """

    agent_id: str
    signal_class_id: str
    horizon: int
    decision_time: datetime

    forecast_distribution: ForecastOverBuckets
    calibrated_forecast: ForecastOverBuckets

    calibrated_expected_return: float
    calibrated_expected_utility: float
    tradable_edge_score: float
    kelly_fraction_applied: float
    final_action: TradeAction | NoAction

    realized_return: float
    realized_bucket: ReturnBucket
    brier: float
    log_score: float
    realized_edge: float


@dataclass
class Scoreboard:
    """Collector for ScoreboardRow records.

    Thin wrapper over a list with metadata-based filtering helpers and per-
    column mean accessors. The MVP API matches the pattern PYRAMID Stone 9
    describes (filter + aggregate); production swaps the backing list for a
    Postgres view over the v5 data spine tables, same API.
    """

    rows: list[ScoreboardRow] = field(default_factory=list)

    def append(self, row: ScoreboardRow) -> None:
        self.rows.append(row)

    # ---- metadata filters ---------------------------------------------------

    def filter_by_horizon(self, horizon: int) -> list[ScoreboardRow]:
        return [r for r in self.rows if r.horizon == horizon]

    def filter_by_signal_class(self, signal_class_id: str) -> list[ScoreboardRow]:
        return [r for r in self.rows if r.signal_class_id == signal_class_id]

    def filter_by_agent(self, agent_id: str) -> list[ScoreboardRow]:
        return [r for r in self.rows if r.agent_id == agent_id]

    # ---- aggregations -------------------------------------------------------

    @staticmethod
    def _mean(rows: list[ScoreboardRow], column: Callable[[ScoreboardRow], float]) -> float:
        if not rows:
            raise ValueError("Cannot take mean over an empty row set.")
        return sum(column(r) for r in rows) / len(rows)

    def mean_brier(self, rows: list[ScoreboardRow] | None = None) -> float:
        return self._mean(rows if rows is not None else self.rows, lambda r: r.brier)

    def mean_log_score(self, rows: list[ScoreboardRow] | None = None) -> float:
        return self._mean(rows if rows is not None else self.rows, lambda r: r.log_score)

    def mean_realized_edge(self, rows: list[ScoreboardRow] | None = None) -> float:
        return self._mean(rows if rows is not None else self.rows, lambda r: r.realized_edge)

    def total_rows(self) -> int:
        return len(self.rows)

    def horizons_seen(self) -> list[int]:
        """Distinct horizons seen in first-seen order."""
        seen: list[int] = []
        seen_set: set[int] = set()
        for r in self.rows:
            if r.horizon in seen_set:
                continue
            seen.append(r.horizon)
            seen_set.add(r.horizon)
        return seen

    # ---- Track C attribution (Stone 11e; Cluster I) -------------------------

    def incremental_ai_edge(
        self,
        ai_agent_id: str,
        baseline_agent_id: str,
    ) -> float:
        """Track C attribution helper: mean(AI realized_edge) - mean(Baseline
        realized_edge), where both means are taken over each agent's slice
        of the Scoreboard (PYRAMID Stone 11e).

        This is THE attribution number. Without it, the AI's absolute
        realized_edge could be repackaged macro beta. With it, only the
        portion of edge that exceeds an information-poor macro baseline
        survives.

        Raises ValueError if either slice is empty (the caller must
        ensure both the AI and the Baseline have logged forecasts).
        """
        ai_rows = self.filter_by_agent(ai_agent_id)
        baseline_rows = self.filter_by_agent(baseline_agent_id)
        if not ai_rows:
            raise ValueError(f"No Scoreboard rows for AI agent_id={ai_agent_id!r}.")
        if not baseline_rows:
            raise ValueError(f"No Scoreboard rows for Baseline agent_id={baseline_agent_id!r}.")
        return self.mean_realized_edge(ai_rows) - self.mean_realized_edge(baseline_rows)


__all__ = ["Scoreboard", "ScoreboardRow"]
