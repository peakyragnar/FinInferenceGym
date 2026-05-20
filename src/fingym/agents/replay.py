"""Replay orchestrator — iterate (ticker, decision_date) pairs and
emit + persist Contracts via the RealLlmAgent.

The replay is the engine that fills the trajectory store with real
Contracts. The Forecast Ledger derives per-signal-class reliability
from these Contracts joined to realized returns once horizons mature.

Idempotent: skips a (ticker, decision_date, agent_id) tuple if a
Contract already exists for it. Re-runs are safe.

Designed to be scale-controllable. The caller picks:
  - The universe (subset of tickers)
  - The decision-date schedule (every-N-trading-days, or explicit list)
  - The horizon (forwarded to the agent)

Costs grow with the schedule density. A 7-ticker, monthly-decision-day,
10-year replay is ~840 LLM calls (~$5-20 with Haiku 4.5, less with
prompt caching). Daily replay is ~17,500 calls (~$50-200).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import psycopg

from fingym.agents.real_agent import RealLlmAgent
from fingym.data.queries.contracts import save_contract


@dataclass(frozen=True)
class ReplayItem:
    ticker: str
    decision_date: date


@dataclass
class ReplayResult:
    """Aggregate of one replay run."""

    started_at: datetime
    attempted: int = 0
    succeeded: int = 0
    skipped_existing: int = 0
    failed: int = 0
    failures: list[tuple[ReplayItem, str]] = field(default_factory=list)
    finished_at: datetime | None = None

    def elapsed_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()


def _trading_days_for_ticker(
    conn: psycopg.Connection[Any], ticker: str, every_n: int
) -> list[date]:
    """Return every Nth trading day in the ticker's available history.

    every_n=1 → daily, every_n=21 ≈ monthly (one per month for equities),
    every_n=63 ≈ quarterly. Anchored to the ticker's actual price calendar
    so we never propose a non-trading day."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of FROM equity_prices
            WHERE ticker = %s ORDER BY as_of ASC
            """,
            (ticker,),
        )
        all_days = [r[0] for r in cur.fetchall()]
    if every_n <= 1:
        return all_days
    return all_days[::every_n]


def _existing_contract_dates(
    conn: psycopg.Connection[Any], ticker: str, agent_id: str
) -> set[date]:
    """Return decision_dates that already have a persisted Contract for
    this (ticker, agent_id). Used for idempotent skips."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT decision_time::date FROM contracts
            WHERE ticker = %s AND agent_id = %s
            """,
            (ticker, agent_id),
        )
        return {r[0] for r in cur.fetchall()}


def build_replay_items(
    conn: psycopg.Connection[Any],
    universe: tuple[str, ...],
    every_n: int,
    agent_id: str,
    skip_existing: bool = True,
    horizon_days: int = 30,
) -> list[ReplayItem]:
    """Build the list of (ticker, decision_date) pairs to replay.

    Filters out:
      - days that already have a persisted Contract for (ticker, agent_id)
        when skip_existing=True
      - days within `horizon_days` of the ticker's last trading day
        (realized returns can't be computed yet)
    """
    items: list[ReplayItem] = []
    for ticker in universe:
        days = _trading_days_for_ticker(conn, ticker, every_n)
        if not days:
            continue
        # Skip the most recent horizon_days — realized returns not yet available
        last_day = days[-1]
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(as_of) FROM equity_prices WHERE ticker = %s",
                (ticker,),
            )
            row = cur.fetchone()
            if row and row[0]:
                last_day = row[0]
        cutoff_idx = len(days)
        for i in range(len(days) - 1, -1, -1):
            delta = (last_day - days[i]).days
            if delta >= horizon_days:
                cutoff_idx = i + 1
                break
        eligible_days = days[:cutoff_idx]

        existing = _existing_contract_dates(conn, ticker, agent_id) if skip_existing else set()
        for d in eligible_days:
            if d in existing:
                continue
            items.append(ReplayItem(ticker=ticker, decision_date=d))
    return items


def run_replay(
    conn: psycopg.Connection[Any],
    agent: RealLlmAgent,
    items: list[ReplayItem],
    progress_every: int = 10,
    sleep_seconds: float = 0.0,
) -> ReplayResult:
    """Execute the replay over an explicit list of items.

    Catches per-item exceptions so a single failure doesn't kill the run.
    Commits after every successful save (idempotent). Optional sleep
    between items for gentler API-rate-limit behavior."""
    started = datetime.now(UTC)
    result = ReplayResult(started_at=started)

    for i, item in enumerate(items, start=1):
        result.attempted += 1
        try:
            contract = agent.forecast_for(conn, item.ticker, item.decision_date)
            save_contract(conn, contract, item.ticker)
            conn.commit()
            result.succeeded += 1
        except Exception as e:
            result.failed += 1
            result.failures.append((item, f"{type(e).__name__}: {e}"))
            conn.rollback()

        if i % progress_every == 0 or i == len(items):
            elapsed = (datetime.now(UTC) - started).total_seconds()
            rate = i / elapsed if elapsed > 0 else 0.0
            print(
                f"  [{i:>5}/{len(items)}] "
                f"succeeded={result.succeeded:>5} failed={result.failed:>3} "
                f"elapsed={elapsed:>6.1f}s rate={rate:.2f}/s"
            )

        if sleep_seconds > 0 and i < len(items):
            time.sleep(sleep_seconds)

    result.finished_at = datetime.now(UTC)
    return result


__all__ = [
    "ReplayItem",
    "ReplayResult",
    "build_replay_items",
    "run_replay",
]
