"""Realized log returns per (ticker, decision_time, horizon).

Computed from equity_prices (split-adjusted closes) joined on trading
days. The horizon is calendar days; we find the closest trading day
on/after decision_time + horizon and compute the log return between
its close and the close at decision_time.

Returns are bucketed using the same 5-bucket structure the toy uses
(below_minus_5 / minus_5_to_0 / zero_to_plus_5 / plus_5_to_plus_10 /
above_plus_10) so the Baseline's Bayesian Ledger keys are compatible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Literal

import psycopg

ReturnBucket = Literal[
    "below_minus_5",
    "minus_5_to_0",
    "zero_to_plus_5",
    "plus_5_to_plus_10",
    "above_plus_10",
]

RETURN_BUCKETS: tuple[ReturnBucket, ...] = (
    "below_minus_5",
    "minus_5_to_0",
    "zero_to_plus_5",
    "plus_5_to_plus_10",
    "above_plus_10",
)


@dataclass(frozen=True)
class RealizedReturn:
    ticker: str
    decision_date: date
    horizon_days: int
    start_close: Decimal
    horizon_date: date
    horizon_close: Decimal
    log_return: float
    bucket: ReturnBucket


def bucket_for_log_return(log_ret: float) -> ReturnBucket:
    """Map a log return to one of five buckets. Boundaries at ±5%, +10% log."""
    if log_ret < -0.05:
        return "below_minus_5"
    if log_ret < 0.0:
        return "minus_5_to_0"
    if log_ret < 0.05:
        return "zero_to_plus_5"
    if log_ret < 0.10:
        return "plus_5_to_plus_10"
    return "above_plus_10"


def _close_at_or_after(
    conn: psycopg.Connection[Any], ticker: str, target: date
) -> tuple[date, Decimal] | None:
    """Return the close on the first trading day on or after `target`."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of, close FROM equity_prices
            WHERE ticker = %s AND as_of >= %s AND close IS NOT NULL
            ORDER BY as_of ASC LIMIT 1
            """,
            (ticker, target),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else None


def _close_at_or_before(
    conn: psycopg.Connection[Any], ticker: str, target: date
) -> tuple[date, Decimal] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of, close FROM equity_prices
            WHERE ticker = %s AND as_of <= %s AND close IS NOT NULL
            ORDER BY as_of DESC LIMIT 1
            """,
            (ticker, target),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else None


def realized_return(
    conn: psycopg.Connection[Any],
    ticker: str,
    decision_date: date,
    horizon_days: int,
) -> RealizedReturn | None:
    """Compute the realized log return for `ticker` from decision_date to
    decision_date + horizon_days. Returns None if either close is missing.

    Uses the first available trading day on/after the target dates (so a
    weekend / holiday decision still snaps to a real bar)."""
    start = _close_at_or_after(conn, ticker, decision_date)
    if start is None:
        return None
    end_target = start[0] + timedelta(days=horizon_days)
    end = _close_at_or_after(conn, ticker, end_target)
    if end is None:
        return None
    start_date, start_close = start
    end_date, end_close = end
    if start_close <= 0 or end_close <= 0:
        return None
    log_ret = math.log(float(end_close) / float(start_close))
    return RealizedReturn(
        ticker=ticker,
        decision_date=start_date,
        horizon_days=horizon_days,
        start_close=start_close,
        horizon_date=end_date,
        horizon_close=end_close,
        log_return=log_ret,
        bucket=bucket_for_log_return(log_ret),
    )


def trading_days(
    conn: psycopg.Connection[Any],
    ticker: str,
    from_date: date,
    to_date: date,
) -> list[date]:
    """All trading-day as_of dates for a ticker in [from_date, to_date]."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of FROM equity_prices
            WHERE ticker = %s AND as_of BETWEEN %s AND %s
            ORDER BY as_of
            """,
            (ticker, from_date, to_date),
        )
        return [r[0] for r in cur.fetchall()]
