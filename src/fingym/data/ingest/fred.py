"""FRED ingest — pulls macro time series into headline_observables.

Reads FRED_API_KEY and DATABASE_URL from process environment. Pulls each
series's full available history with current-vintage values. Inserts into
headline_observables with vintage=1.

PIT caveat: for series that revise (CPI, NFP, GDP, etc.), as_known here
is the realtime_start of the CURRENT vintage, not the first-print date.
True first-print PIT requires an ALFRED vintage-tracking ingest pass,
which is future work (the parked materiality/emissions stone). Market
data (rates, VIX, FX, commodities) does not revise materially, so
as_known ≈ as_of for those.

Run:
    uv run --env-file .env python -m fingym.data.ingest.fred
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any, cast

import psycopg

FRED_BASE = "https://api.stlouisfed.org/fred"

SERIES_TO_INGEST: tuple[str, ...] = (
    "DFF",
    "FEDFUNDS",
    "DGS3MO",
    "DGS2",
    "DGS5",
    "DGS10",
    "DGS30",
    "T10Y2Y",
    "T5YIFR",
    "T10YIE",
    "VIXCLS",
    "DTWEXBGS",
    "DEXUSEU",
    "DEXJPUS",
    "DEXCHUS",
    "DCOILWTICO",
    "DCOILBRENTEU",
    "PCOPPUSDM",
    "CPIAUCSL",
    "CPILFESL",
    "PCEPI",
    "PCEPILFE",
    "PAYEMS",
    "UNRATE",
    "INDPRO",
    "RSAFS",
    "HOUST",
    "GDPC1",
    "ICSA",
    "CCSA",
    "WALCL",
    "M2SL",
)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"missing {name} in environment (use --env-file .env)")
    return value


def _fred_get(path: str, params: dict[str, str], key: str) -> dict[str, Any]:
    full = {**params, "api_key": key, "file_type": "json"}
    url = f"{FRED_BASE}{path}?{urllib.parse.urlencode(full)}"
    req = urllib.request.Request(url, headers={"User-Agent": "fingym-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


def fetch_observations(series_id: str, key: str) -> list[dict[str, Any]]:
    """Pull every observation for a series (current vintage, ascending date)."""
    result = _fred_get(
        "/series/observations",
        {"series_id": series_id, "limit": "100000", "sort_order": "asc"},
        key,
    )
    obs = result.get("observations", [])
    return cast(list[dict[str, Any]], obs)


def _coerce_rows(series_id: str, observations: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for obs in observations:
        value_str = obs.get("value", ".")
        if value_str in (".", "", None):
            continue
        try:
            value = Decimal(str(value_str))
        except Exception:
            continue
        as_of = obs.get("date")
        as_known = obs.get("realtime_start")
        if not as_of or not as_known:
            continue
        rows.append((series_id, as_of, as_known, value, "FRED", 1))
    return rows


def upsert_rows(conn: psycopg.Connection[Any], rows: list[tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO headline_observables
                (series_id, as_of, as_known, value, source, vintage)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (series_id, as_of, vintage) DO UPDATE
                SET value = EXCLUDED.value,
                    as_known = EXCLUDED.as_known,
                    source = EXCLUDED.source
            """,
            rows,
        )
    return len(rows)


def main() -> None:
    fred_key = _require_env("FRED_API_KEY")
    db_url = _require_env("DATABASE_URL")

    print(f"FRED ingest — {len(SERIES_TO_INGEST)} series -> headline_observables")

    total = 0
    with psycopg.connect(db_url) as conn:
        for sid in SERIES_TO_INGEST:
            try:
                obs = fetch_observations(sid, fred_key)
            except Exception as e:
                print(f"  {sid:14}  FETCH FAILED — {e}")
                continue
            rows = _coerce_rows(sid, obs)
            n = upsert_rows(conn, rows)
            conn.commit()
            earliest = rows[0][1] if rows else "—"
            latest = rows[-1][1] if rows else "—"
            print(f"  {sid:14}  {n:>7} rows   {earliest} → {latest}")
            total += n

    print(f"\nTotal: {total} rows across {len(SERIES_TO_INGEST)} series")


if __name__ == "__main__":
    main()
