"""Read adapter for the headline_observables Postgres table.

Returns the latest known value per series at decision time t. Honors PIT
discipline by filtering on as_known <= decision_time.

The Baseline-input series (DESIGN.md "Operator Configuration" envelope —
rates / vol / FX / commodities) is a narrow 7-series subset of the full
table. The full table also holds macro-emission series (CPI, NFP, etc.)
that the AI Core consumes; the Baseline does not see those by design.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import psycopg

# The 7 series the Market-State Baseline conditions on (per real_data_ingest.md
# Stage 1 "wire Baseline" step). Operator-tunable per DESIGN.md "Operator
# Configuration and Observability."
BASELINE_SERIES: tuple[str, ...] = (
    "DFF",  # Daily Fed Funds — policy rate
    "DGS10",  # 10y Treasury yield — long rate level
    "T10Y2Y",  # 10y-2y curve spread
    "T5YIFR",  # 5y5y forward inflation expectations
    "VIXCLS",  # CBOE VIX — equity vol regime
    "DTWEXBGS",  # Broad US dollar index
    "DCOILWTICO",  # WTI crude oil
)


def latest_value_at(
    conn: psycopg.Connection[Any], series_id: str, decision_time: datetime
) -> Decimal | None:
    """Return the most recent value for `series_id` with as_known <= decision_time.

    PIT-disciplined: an agent at decision time t cannot see anything published
    after t. Returns None if no observation is knowable at t.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT value FROM headline_observables
            WHERE series_id = %s
              AND as_known <= %s
              AND value IS NOT NULL
            ORDER BY as_of DESC, as_known DESC, vintage DESC
            LIMIT 1
            """,
            (series_id, decision_time),
        )
        row = cur.fetchone()
    return row[0] if row else None


def baseline_state_at(conn: psycopg.Connection[Any], decision_time: datetime) -> dict[str, Decimal]:
    """Return the latest known value per BASELINE_SERIES at decision_time.

    Series with no known observation at t are omitted (caller decides whether
    that's a hard failure or graceful degradation).
    """
    out: dict[str, Decimal] = {}
    for series_id in BASELINE_SERIES:
        value = latest_value_at(conn, series_id, decision_time)
        if value is not None:
            out[series_id] = value
    return out


def median_per_series(
    conn: psycopg.Connection[Any],
    earliest: date | None = None,
    latest: date | None = None,
) -> dict[str, Decimal]:
    """Compute the historical median per BASELINE_SERIES. Used to set
    bucket cutpoints (median split = 2 buckets per series).

    Optional date range filter; defaults to all available history.
    """
    out: dict[str, Decimal] = {}
    with conn.cursor() as cur:
        for series_id in BASELINE_SERIES:
            params: list[Any] = [series_id]
            where = "series_id = %s AND value IS NOT NULL"
            if earliest is not None:
                where += " AND as_of >= %s"
                params.append(earliest)
            if latest is not None:
                where += " AND as_of <= %s"
                params.append(latest)
            cur.execute(
                f"""
                SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY value)
                FROM headline_observables
                WHERE {where}
                """,
                params,
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                out[series_id] = row[0]
    return out


def values_in_range(
    conn: psycopg.Connection[Any],
    series_id: str,
    from_date: date,
    to_date: date,
) -> list[tuple[date, Decimal]]:
    """Return all (as_of, value) pairs for a series in [from_date, to_date]
    using the latest known value per as_of (most recent vintage)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (as_of) as_of, value
            FROM headline_observables
            WHERE series_id = %s
              AND as_of BETWEEN %s AND %s
              AND value IS NOT NULL
            ORDER BY as_of, as_known DESC, vintage DESC
            """,
            (series_id, from_date, to_date),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


def _decision_close_ts(d: date) -> datetime:
    """Standard close-of-day timestamp used for PIT queries on a trading date."""
    return datetime(d.year, d.month, d.day, 21, 0, 0, tzinfo=UTC)
