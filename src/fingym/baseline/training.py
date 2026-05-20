"""Train the RealMarketStateBaseline from historical headline_observables
+ equity_prices.

Batched: one SQL query per data type (8 queries total — 1 for cutpoints,
1 per Baseline series, 1 per ticker for prices). All subsequent lookups
are in-memory bisects. Runs in seconds on the full test universe.

Procedure:
  1. Compute median cutpoints per BASELINE_SERIES (1 query each).
  2. Bulk-load each Baseline series's (as_of, value) into memory.
  3. Bulk-load each ticker's (as_of, close) into memory.
  4. For each (ticker, trading-day) pair, bisect the macro and price
     timelines to get the macro state at decision day and the realized
     return at horizon_days.
  5. Record into the Baseline. Report cells / observations / forecast.

Run:
    uv run --env-file .env python -m fingym.baseline.training
"""

from __future__ import annotations

import bisect
import math
import os
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg

from fingym.baseline.real_market_state import (
    REAL_BASELINE_AGENT_ID,
    RealMarketStateBaseline,
    state_key_from_values,
)
from fingym.data.queries.equity_returns import bucket_for_log_return
from fingym.data.queries.headline_observables import (
    BASELINE_SERIES,
    median_per_series,
)

# Test universe — mirror of fingym.data.ingest.massive.TEST_UNIVERSE
TEST_UNIVERSE: tuple[str, ...] = (
    "AAPL",
    "JPM",
    "TSLA",
    "NVDA",
    "VST",
    "SIVB",
    "TWTR",
)

DEFAULT_HORIZON_DAYS = 30


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"missing {name} in environment (use --env-file .env)")
    return value


def _load_series_timeline(
    conn: psycopg.Connection[Any], series_id: str
) -> tuple[list[date], list[Decimal]]:
    """Load all (as_of, value) pairs for a series, sorted by as_of."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (as_of) as_of, value
            FROM headline_observables
            WHERE series_id = %s AND value IS NOT NULL
            ORDER BY as_of, as_known DESC, vintage DESC
            """,
            (series_id,),
        )
        rows = cur.fetchall()
    dates = [r[0] for r in rows]
    values = [r[1] for r in rows]
    return dates, values


def _load_ticker_prices(
    conn: psycopg.Connection[Any], ticker: str
) -> tuple[list[date], list[Decimal]]:
    """Load all (as_of, close) pairs for a ticker, sorted by as_of."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of, close FROM equity_prices
            WHERE ticker = %s AND close IS NOT NULL
            ORDER BY as_of
            """,
            (ticker,),
        )
        rows = cur.fetchall()
    dates = [r[0] for r in rows]
    closes = [r[1] for r in rows]
    return dates, closes


def _latest_value_at(
    dates: list[date], values: list[Decimal], decision_day: date
) -> Decimal | None:
    """Bisect for the latest value with as_of <= decision_day."""
    idx = bisect.bisect_right(dates, decision_day)
    if idx == 0:
        return None
    return values[idx - 1]


def _close_on_or_after(
    dates: list[date], closes: list[Decimal], target: date
) -> tuple[date, Decimal] | None:
    """Bisect for the first close on or after target."""
    idx = bisect.bisect_left(dates, target)
    if idx >= len(dates):
        return None
    return dates[idx], closes[idx]


def train_baseline(
    conn: psycopg.Connection[Any], universe: tuple[str, ...], horizon_days: int
) -> RealMarketStateBaseline:
    print("Computing median cutpoints per BASELINE_SERIES...")
    cutpoints = median_per_series(conn)
    print("Cutpoints (series, median):")
    for series_id in BASELINE_SERIES:
        cp = cutpoints.get(series_id)
        print(f"  {series_id:12} {cp}")
    missing = [s for s in BASELINE_SERIES if s not in cutpoints]
    if missing:
        sys.exit(f"missing median for series: {missing}")

    baseline = RealMarketStateBaseline(series_order=BASELINE_SERIES, cutpoints=cutpoints)

    # Bulk-load all macro series timelines
    print("\nBulk-loading macro series...")
    macro: dict[str, tuple[list[date], list[Decimal]]] = {}
    for series_id in BASELINE_SERIES:
        macro[series_id] = _load_series_timeline(conn, series_id)
        print(f"  {series_id:12} {len(macro[series_id][0]):>6} obs")

    print(f"\nTraining on {len(universe)} tickers, horizon = {horizon_days} days")
    print(f"{'Ticker':<7} {'days':>6} {'recorded':>10} {'skipped':>8}")
    print("-" * 36)

    for ticker in universe:
        price_dates, price_closes = _load_ticker_prices(conn, ticker)
        if not price_dates:
            print(f"{ticker:<7} no price data; skipping")
            continue

        recorded = 0
        skipped = 0
        # Iterate trading days where the realized return at horizon is computable
        last_horizon_target = price_dates[-1] - timedelta(days=horizon_days)
        # Find decision days up to the cutoff
        cutoff_idx = bisect.bisect_right(price_dates, last_horizon_target)
        decision_days = price_dates[:cutoff_idx]
        decision_closes = price_closes[:cutoff_idx]

        for i, d in enumerate(decision_days):
            # Macro state at decision day
            state: dict[str, Decimal] = {}
            for series_id in BASELINE_SERIES:
                dates, values = macro[series_id]
                val = _latest_value_at(dates, values, d)
                if val is None:
                    break
                state[series_id] = val
            if len(state) < len(BASELINE_SERIES):
                skipped += 1
                continue

            # Realized return at horizon
            start_close = decision_closes[i]
            target = d + timedelta(days=horizon_days)
            end = _close_on_or_after(price_dates, price_closes, target)
            if end is None:
                skipped += 1
                continue
            _, end_close = end
            if start_close <= 0 or end_close <= 0:
                skipped += 1
                continue
            log_ret = math.log(float(end_close) / float(start_close))
            bucket = bucket_for_log_return(log_ret)

            ok = baseline.record(state, bucket)
            if ok:
                recorded += 1
            else:
                skipped += 1

        print(f"{ticker:<7} {len(decision_days):>6} {recorded:>10} {skipped:>8}")

    return baseline


def report_baseline(baseline: RealMarketStateBaseline) -> None:
    print()
    print(f"Cells populated: {baseline.cells_populated()} / {2 ** len(BASELINE_SERIES)}")
    print(f"Total observations recorded: {baseline.total_observations()}")

    by_size = sorted(
        ((key, sum(counts.values())) for key, counts in baseline.cell_counts.items()),
        key=lambda x: -x[1],
    )
    print("\nTop 10 cells by sample size:")
    print(f"  {'state':<60} {'n':>5} {'<-5%':>6} {'-5_0':>6} {'0_5':>6} {'5_10':>6} {'>10':>6}")
    for key, n in by_size[:10]:
        counts = baseline.cell_counts[key]
        key_str = " ".join(
            f"{s[:4]}={b[0].upper()}" for s, b in zip(baseline.series_order, key, strict=False)
        )
        print(
            f"  {key_str:<60} {n:>5} "
            f"{counts['below_minus_5']:>6} {counts['minus_5_to_0']:>6} "
            f"{counts['zero_to_plus_5']:>6} {counts['plus_5_to_plus_10']:>6} "
            f"{counts['above_plus_10']:>6}"
        )


def show_current_forecast(conn: psycopg.Connection[Any], baseline: RealMarketStateBaseline) -> None:
    """Pull today's macro state and ask the Baseline for its 1m forecast."""
    today = date.today()
    print("\nCurrent macro state (as of latest available data):")
    state: dict[str, Decimal] = {}
    for series_id in BASELINE_SERIES:
        dates, values = _load_series_timeline(conn, series_id)
        val = _latest_value_at(dates, values, today)
        cp = baseline.cutpoints.get(series_id)
        if val is None or cp is None:
            print(f"  {series_id:12} (missing)")
            continue
        bucket = "low" if val < cp else "high"
        state[series_id] = val
        print(f"  {series_id:12} value={val} median={cp} → {bucket}")

    key = state_key_from_values(state, baseline.cutpoints, baseline.series_order)
    if key is None:
        print("  (incomplete state; uniform forecast)")
        return
    n = baseline.cell_sample_size(state)
    fc = baseline.forecast(state)
    print(f"\nBaseline forecast for current state (cell n={n}):")
    for bucket, prob in fc.items():
        bar = "█" * int(prob * 40)
        print(f"  {bucket:<20} {prob:>6.3f} {bar}")


def main() -> None:
    db_url = _require_env("DATABASE_URL")
    horizon = int(os.environ.get("BASELINE_HORIZON_DAYS", DEFAULT_HORIZON_DAYS))
    start = datetime.now(UTC)
    with psycopg.connect(db_url) as conn:
        baseline = train_baseline(conn, TEST_UNIVERSE, horizon)
        report_baseline(baseline)
        show_current_forecast(conn, baseline)
    elapsed = (datetime.now(UTC) - start).total_seconds()
    print(f"\nBaseline trained ({REAL_BASELINE_AGENT_ID}). Elapsed: {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
