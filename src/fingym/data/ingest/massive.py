"""Massive (Polygon) ingest — Stage 1 deterministic equity data.

Reads MASSIVE_API_KEY and DATABASE_URL from process environment. Pulls
the five Stage 1 endpoints for the configured test universe:

  - ticker reference (active + delisted)  → tickers table
  - daily OHLCV bars                      → equity_prices table
  - splits                                → corporate_actions_splits
  - cash dividends                        → corporate_actions_dividends
  - IPOs                                  → ipos table

Stage 1 ingests only deterministic facts — no curation choices. See
real_data_ingest.md "Stage 1" for the design.

PIT semantics for equity_prices:
  - as_of      = the trading date (Massive's `t` timestamp converted to date)
  - as_known   = the same date + close timestamp (16:00 ET / 21:00 UTC)
                 daily prices don't revise; vintage stays 1

Run:
    uv run --env-file .env python -m fingym.data.ingest.massive
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import psycopg

MASSIVE_BASE = "https://api.polygon.io"

# Stage 1 test universe — 5 operating + 2 delisted. See real_data_ingest.md.
TEST_UNIVERSE: tuple[str, ...] = (
    "AAPL",  # large-cap tech, consumer hardware
    "JPM",  # large-cap bank, financial-sector statement shape
    "TSLA",  # large-cap auto/EV, high volatility, news-heavy
    "NVDA",  # large-cap semis / AI
    "VST",  # utility / power generation (AI-infra thesis name)
    "SIVB",  # delisted 2023 (SVB collapse) — survivorship test #1
    "TWTR",  # delisted 2022 (taken private) — survivorship test #2
)

# Massive Developer tier: 10-year price history.
HISTORY_YEARS = 10


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"missing {name} in environment (use --env-file .env)")
    return value


def _massive_get(path: str, params: dict[str, str], key: str) -> dict[str, Any]:
    full = {**params, "apiKey": key}
    url = f"{MASSIVE_BASE}{path}?{urllib.parse.urlencode(full)}"
    req = urllib.request.Request(url, headers={"User-Agent": "fingym-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


def _close_ts(trading_date: date) -> datetime:
    """A reasonable as_known for a daily bar: 21:00 UTC (16:00 ET) on the trading day."""
    return datetime(trading_date.year, trading_date.month, trading_date.day, 21, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Endpoint fetchers
# ---------------------------------------------------------------------------


def fetch_ticker_reference(ticker: str, key: str) -> dict[str, Any] | None:
    """Pull ticker metadata. Returns None if the ticker isn't found in active=true.
    If 404, retries with active=false to catch delisted names."""
    # Try the direct single-ticker endpoint first
    try:
        result = _massive_get(f"/v3/reference/tickers/{ticker}", {}, key)
        results = result.get("results")
        if isinstance(results, dict):
            return results
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    # Direct endpoint may 404 for delisted tickers; fall back to the listing
    # endpoint with active=false to catch them.
    result = _massive_get(
        "/v3/reference/tickers",
        {"ticker": ticker, "active": "false", "limit": "10"},
        key,
    )
    seriess = result.get("results") or []
    if isinstance(seriess, list) and seriess:
        first = seriess[0]
        if isinstance(first, dict):
            return first
    return None


def fetch_ohlcv(ticker: str, from_date: date, to_date: date, key: str) -> list[dict[str, Any]]:
    """Pull daily OHLCV bars (split-adjusted; Massive default)."""
    path = f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date.isoformat()}/{to_date.isoformat()}"
    result = _massive_get(path, {"adjusted": "true", "sort": "asc", "limit": "50000"}, key)
    results = result.get("results") or []
    return cast(list[dict[str, Any]], results)


def fetch_splits(ticker: str, key: str) -> list[dict[str, Any]]:
    result = _massive_get(
        "/v3/reference/splits", {"ticker": ticker, "limit": "1000", "order": "asc"}, key
    )
    results = result.get("results") or []
    return cast(list[dict[str, Any]], results)


def fetch_dividends(ticker: str, key: str) -> list[dict[str, Any]]:
    result = _massive_get(
        "/v3/reference/dividends",
        {"ticker": ticker, "limit": "1000", "order": "asc"},
        key,
    )
    results = result.get("results") or []
    return cast(list[dict[str, Any]], results)


def fetch_ipos(ticker: str, key: str) -> list[dict[str, Any]]:
    try:
        result = _massive_get("/vX/reference/ipos", {"ticker": ticker, "limit": "100"}, key)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return []
        raise
    results = result.get("results") or []
    return cast(list[dict[str, Any]], results)


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------


def upsert_ticker(conn: psycopg.Connection[Any], ticker: str, info: dict[str, Any]) -> int:
    if not info:
        return 0
    snapshot = date.today()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tickers (
                ticker, snapshot_date, name, market, primary_exchange,
                ticker_type, active, delisted_utc, cik, composite_figi,
                share_class_figi, last_updated_utc, currency_name, locale, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
                name = EXCLUDED.name,
                market = EXCLUDED.market,
                primary_exchange = EXCLUDED.primary_exchange,
                ticker_type = EXCLUDED.ticker_type,
                active = EXCLUDED.active,
                delisted_utc = EXCLUDED.delisted_utc,
                cik = EXCLUDED.cik,
                composite_figi = EXCLUDED.composite_figi,
                share_class_figi = EXCLUDED.share_class_figi,
                last_updated_utc = EXCLUDED.last_updated_utc,
                currency_name = EXCLUDED.currency_name,
                locale = EXCLUDED.locale
            """,
            (
                ticker,
                snapshot,
                info.get("name"),
                info.get("market"),
                info.get("primary_exchange"),
                info.get("type"),
                bool(info.get("active", False)),
                info.get("delisted_utc"),
                info.get("cik"),
                info.get("composite_figi"),
                info.get("share_class_figi"),
                info.get("last_updated_utc"),
                info.get("currency_name"),
                info.get("locale"),
                "massive",
            ),
        )
    return 1


def upsert_ohlcv(conn: psycopg.Connection[Any], ticker: str, bars: list[dict[str, Any]]) -> int:
    if not bars:
        return 0
    rows: list[tuple[Any, ...]] = []
    for bar in bars:
        t_ms = bar.get("t")
        if t_ms is None:
            continue
        as_of_date = datetime.fromtimestamp(t_ms / 1000.0, tz=UTC).date()
        rows.append(
            (
                ticker,
                as_of_date,
                _close_ts(as_of_date),
                _to_decimal(bar.get("o")),
                _to_decimal(bar.get("h")),
                _to_decimal(bar.get("l")),
                _to_decimal(bar.get("c")),
                bar.get("v"),
                _to_decimal(bar.get("vw")),
                bar.get("n"),
                "massive",
                1,
            )
        )
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO equity_prices (
                ticker, as_of, as_known, open, high, low, close,
                volume, vwap, transactions, source, vintage
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, as_of, vintage) DO UPDATE SET
                as_known = EXCLUDED.as_known,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                vwap = EXCLUDED.vwap,
                transactions = EXCLUDED.transactions
            """,
            rows,
        )
    return len(rows)


def upsert_splits(conn: psycopg.Connection[Any], events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    rows: list[tuple[Any, ...]] = []
    for e in events:
        rows.append(
            (
                e.get("ticker"),
                e.get("execution_date"),
                _to_decimal(e.get("split_from")),
                _to_decimal(e.get("split_to")),
                "massive",
            )
        )
    rows = [r for r in rows if r[0] and r[1] and r[2] and r[3]]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO corporate_actions_splits (
                ticker, ex_date, split_from, split_to, source
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ticker, ex_date) DO UPDATE SET
                split_from = EXCLUDED.split_from,
                split_to = EXCLUDED.split_to
            """,
            rows,
        )
    return len(rows)


def upsert_dividends(conn: psycopg.Connection[Any], events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    rows: list[tuple[Any, ...]] = []
    for e in events:
        cash = _to_decimal(e.get("cash_amount"))
        if cash is None:
            continue
        rows.append(
            (
                e.get("ticker"),
                e.get("ex_dividend_date"),
                e.get("declaration_date"),
                e.get("record_date"),
                e.get("pay_date"),
                cash,
                e.get("dividend_type"),
                e.get("frequency"),
                e.get("currency"),
                "massive",
            )
        )
    rows = [r for r in rows if r[0] and r[1]]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO corporate_actions_dividends (
                ticker, ex_date, declaration_date, record_date, pay_date,
                cash_amount, dividend_type, frequency, currency, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, ex_date, cash_amount) DO UPDATE SET
                declaration_date = EXCLUDED.declaration_date,
                record_date = EXCLUDED.record_date,
                pay_date = EXCLUDED.pay_date,
                dividend_type = EXCLUDED.dividend_type,
                frequency = EXCLUDED.frequency,
                currency = EXCLUDED.currency
            """,
            rows,
        )
    return len(rows)


def upsert_ipos(conn: psycopg.Connection[Any], events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    rows: list[tuple[Any, ...]] = []
    for e in events:
        ticker = e.get("ticker")
        ipo_date_str = e.get("listing_date") or e.get("announced_date")
        if not ticker or not ipo_date_str:
            continue
        rows.append(
            (
                ticker,
                ipo_date_str,
                _to_decimal(e.get("final_issue_price")),
                e.get("total_shares_outstanding"),
                e.get("issuer_name"),
                e.get("primary_exchange"),
                e.get("ipo_status"),
                "massive",
            )
        )
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO ipos (
                ticker, ipo_date, final_issue_price, shares_outstanding,
                issuer_name, primary_exchange, ipo_status, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, ipo_date) DO UPDATE SET
                final_issue_price = EXCLUDED.final_issue_price,
                shares_outstanding = EXCLUDED.shares_outstanding,
                issuer_name = EXCLUDED.issuer_name,
                primary_exchange = EXCLUDED.primary_exchange,
                ipo_status = EXCLUDED.ipo_status
            """,
            rows,
        )
    return len(rows)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def ingest_ticker(
    conn: psycopg.Connection[Any],
    ticker: str,
    key: str,
    from_date: date,
    to_date: date,
) -> dict[str, int]:
    """Pull all 5 endpoints for one ticker. Returns row counts per table."""
    counts: dict[str, int] = {}

    info = fetch_ticker_reference(ticker, key)
    counts["tickers"] = upsert_ticker(conn, ticker, info or {})

    bars = fetch_ohlcv(ticker, from_date, to_date, key)
    counts["equity_prices"] = upsert_ohlcv(conn, ticker, bars)

    splits = fetch_splits(ticker, key)
    counts["corporate_actions_splits"] = upsert_splits(conn, splits)

    dividends = fetch_dividends(ticker, key)
    counts["corporate_actions_dividends"] = upsert_dividends(conn, dividends)

    ipos = fetch_ipos(ticker, key)
    counts["ipos"] = upsert_ipos(conn, ipos)

    return counts


def main() -> None:
    key = _require_env("MASSIVE_API_KEY")
    db_url = _require_env("DATABASE_URL")

    to_date = date.today()
    from_date = to_date - timedelta(days=365 * HISTORY_YEARS)

    print(f"Massive Stage 1 ingest — {len(TEST_UNIVERSE)} tickers")
    print(f"Date range: {from_date} → {to_date}")
    print()

    totals: dict[str, int] = {
        "tickers": 0,
        "equity_prices": 0,
        "corporate_actions_splits": 0,
        "corporate_actions_dividends": 0,
        "ipos": 0,
    }

    header = f"{'Ticker':<7} {'tickers':>8} {'prices':>8} {'splits':>7} {'divs':>7} {'ipos':>5}"
    print(header)
    print("-" * len(header))

    with psycopg.connect(db_url) as conn:
        for ticker in TEST_UNIVERSE:
            try:
                counts = ingest_ticker(conn, ticker, key, from_date, to_date)
            except Exception as e:
                print(f"{ticker:<7}  FAILED — {e}")
                continue
            conn.commit()
            print(
                f"{ticker:<7} "
                f"{counts['tickers']:>8} "
                f"{counts['equity_prices']:>8} "
                f"{counts['corporate_actions_splits']:>7} "
                f"{counts['corporate_actions_dividends']:>7} "
                f"{counts['ipos']:>5}"
            )
            for k, v in counts.items():
                totals[k] += v

    print()
    print("Totals:")
    for table, n in totals.items():
        print(f"  {table}: {n}")


if __name__ == "__main__":
    main()
