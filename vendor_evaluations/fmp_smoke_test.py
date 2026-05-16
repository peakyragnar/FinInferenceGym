"""FMP (Financial Modeling Prep) /stable/ API smoke test.

FMP rebranded to a `/stable/` URL pattern after Aug 2025 (legacy
`/api/v3/...` endpoints are 403'd). This script targets the new surface.

Verifies the architecture-critical questions:
  1. DELISTED COVERAGE: known delisted tickers (LEH, ENE, BSC, WAMUQ, MF)
     against profile + historical prices + fundamentals, plus the dedicated
     /stable/delisted-companies endpoint.
  2. PIT FUNDAMENTALS: filingDate + acceptedDate fields on income statement
     filings. GE 2017 across multiple filings to look for restatement
     tracking.
  3. TRANSCRIPTS: confirm the transcript endpoint works (already used by
     Michael for the existing 10-year/1700-name corpus).

Reads FMP_API_KEY from .env. Never prints the key. Run:

    uv run python vendor_evaluations/fmp_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"

BASE = "https://financialmodelingprep.com"


def _load_key() -> str:
    if not ENV_PATH.exists():
        sys.exit(f"missing .env at {ENV_PATH}")
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("FMP_API_KEY="):
            value = line.split("=", 1)[1].strip()
            return value.strip("'\"")
    sys.exit("FMP_API_KEY not present in .env")


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}...{key[-3:]} (len={len(key)})"


def _fetch(path: str, key: str) -> tuple[int, Any]:
    sep = "&" if "?" in path else "?"
    url = f"{BASE}{path}{sep}apikey={key}"
    req = urllib.request.Request(url, headers={"User-Agent": "fingym-smoke/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except Exception as e:
        return -1, f"transport error: {type(e).__name__}: {e}"


def _truncate(value: Any, limit: int = 220) -> str:
    s = repr(value)
    return s if len(s) <= limit else s[:limit] + "..."


# ---------------------------------------------------------------------------
# Smoke checks.
# ---------------------------------------------------------------------------


DELISTED_TICKERS = [
    ("LEH", "Lehman Brothers (pre-BK)", "2008-08-01", "2008-09-15"),
    ("ENE", "Enron (pre-BK, NYSE)", "2001-10-01", "2001-11-30"),
    ("BSC", "Bear Stearns (pre-JPM)", "2008-02-01", "2008-03-17"),
    ("WAMUQ", "Washington Mutual (BK)", "2008-09-01", "2008-09-26"),
    ("MF", "MF Global (pre-BK)", "2011-09-01", "2011-10-31"),
]


def smoke_delisted(key: str) -> None:
    print()
    print("=" * 78)
    print(" Q1. DELISTED COVERAGE (probe known delisted names)")
    print("=" * 78)

    for ticker, name, from_date, to_date in DELISTED_TICKERS:
        print(f"\n--- {ticker} ({name}) ---")

        # Profile
        status, body = _fetch(f"/stable/profile?symbol={ticker}", key)
        if isinstance(body, list) and body:
            p = body[0]
            print(
                f"  profile {status}: name={p.get('companyName')!r}  "
                f"isActivelyTrading={p.get('isActivelyTrading')}  "
                f"ipoDate={p.get('ipoDate')!r}  "
                f"delistedDate={p.get('delistedDate')!r}"
            )
        elif isinstance(body, list):
            print(f"  profile {status}: empty (no profile record)")
        else:
            print(f"  profile {status}: {_truncate(body)}")

        # Historical OHLC over the window of interest
        status, body = _fetch(
            f"/stable/historical-price-eod/full?symbol={ticker}&from={from_date}&to={to_date}",
            key,
        )
        if isinstance(body, list):
            print(
                f"  historical-price-eod/full {status} ({from_date} -> {to_date}): {len(body)} bars"
            )
            for bar in body[:2]:
                print(f"      {bar}")
        elif isinstance(body, dict):
            historical = body.get("historical") or []
            print(
                f"  historical-price-eod/full {status} "
                f"({from_date} -> {to_date}): {len(historical)} bars (dict response)"
            )
            for bar in historical[:2]:
                print(f"      {bar}")
        else:
            print(f"  historical-price-eod/full {status}: {_truncate(body)}")

        # Income statement
        status, body = _fetch(
            f"/stable/income-statement?symbol={ticker}&limit=3&period=annual",
            key,
        )
        if isinstance(body, list):
            print(f"  income-statement {status}: {len(body)} filings")
            if body:
                first = body[0]
                if isinstance(first, dict):
                    pit_fields = {
                        k: first.get(k)
                        for k in (
                            "date",
                            "filingDate",
                            "acceptedDate",
                            "calendarYear",
                            "period",
                            "link",
                            "finalLink",
                            "cik",
                        )
                        if k in first
                    }
                    print(f"      pit-relevant on first: {pit_fields}")
        else:
            print(f"  income-statement {status}: {_truncate(body)}")


def smoke_delisted_list(key: str) -> None:
    print()
    print("=" * 78)
    print(" Q1b. DEDICATED DELISTED-COMPANIES ENDPOINT")
    print("=" * 78)
    status, body = _fetch("/stable/delisted-companies?limit=20", key)
    if isinstance(body, list):
        print(f"  status {status}: {len(body)} entries returned (first 20)")
        for entry in body[:15]:
            if isinstance(entry, dict):
                print(
                    f"    {entry.get('symbol')!r:>12} "
                    f"{(entry.get('companyName') or '')[:40]:<40} "
                    f"ipo={entry.get('ipoDate')} "
                    f"delisted={entry.get('delistedDate')}"
                )
    else:
        print(f"  status {status}: {_truncate(body)}")


def smoke_pit_fundamentals(key: str) -> None:
    print()
    print("=" * 78)
    print(" Q2. PIT FUNDAMENTALS — filingDate + acceptedDate + restatement check")
    print("=" * 78)

    print("\n--- /stable/income-statement?symbol=GE&period=annual (10 most recent) ---")
    status, body = _fetch("/stable/income-statement?symbol=GE&limit=10&period=annual", key)
    if isinstance(body, list):
        print(f"  status {status}: {len(body)} annual filings")
        for entry in body[:5]:
            if isinstance(entry, dict):
                print(
                    f"    date={entry.get('date')}  "
                    f"period={entry.get('period')}  "
                    f"calendarYear={entry.get('calendarYear')}  "
                    f"filingDate={entry.get('filingDate')}  "
                    f"acceptedDate={entry.get('acceptedDate')}  "
                    f"revenue={entry.get('revenue')}"
                )
    else:
        print(f"  status {status}: {_truncate(body)}")

    # Look specifically for GE 2017 (known restatement event)
    print("\n--- GE 2017 — look for multiple filings on same period (restatement) ---")
    status, body = _fetch("/stable/income-statement?symbol=GE&limit=40&period=annual", key)
    if isinstance(body, list):
        by_year: dict[Any, list[dict[str, Any]]] = {}
        for entry in body:
            if isinstance(entry, dict):
                year = entry.get("calendarYear")
                by_year.setdefault(year, []).append(entry)
        print(f"  total annual filings returned: {len(body)}")
        print("  filings per calendarYear (>1 indicates restatement tracking):")
        for year, filings in sorted(by_year.items(), key=lambda x: str(x[0])):
            marker = "  <-- multiple!" if len(filings) > 1 else ""
            print(f"    {year}: {len(filings)}{marker}")

        # Drill into 2017 specifically
        filings_2017 = by_year.get("2017") or by_year.get(2017) or []
        if not filings_2017:
            # Try string year
            filings_2017 = [
                e for e in body if isinstance(e, dict) and str(e.get("calendarYear")) == "2017"
            ]
        if filings_2017:
            print(f"\n  GE 2017 filings ({len(filings_2017)}):")
            for entry in filings_2017:
                print(
                    f"    date={entry.get('date')}  "
                    f"filingDate={entry.get('filingDate')}  "
                    f"acceptedDate={entry.get('acceptedDate')}  "
                    f"revenue={entry.get('revenue')}  "
                    f"netIncome={entry.get('netIncome')}"
                )
        else:
            print("  no GE 2017 filing in the response")

    # Try the "as reported" endpoint to see if it differs
    print("\n--- /stable/income-statement-as-reported?symbol=GE (raw XBRL) ---")
    status, body = _fetch(
        "/stable/income-statement-as-reported?symbol=GE&limit=3&period=annual",
        key,
    )
    if isinstance(body, list):
        print(f"  status {status}: {len(body)} filings")
        if body:
            entry = body[0]
            if isinstance(entry, dict):
                date_keys = [
                    k
                    for k in entry.keys()
                    if any(s in k.lower() for s in ("date", "filing", "accept", "period"))
                ]
                print(f"      first filing has {len(entry)} fields total")
                print(f"      date/filing-related keys: {date_keys}")
                for k in date_keys[:6]:
                    print(f"        {k}: {entry.get(k)}")
    else:
        print(f"  status {status}: {_truncate(body)}")


def smoke_transcripts(key: str) -> None:
    print()
    print("=" * 78)
    print(" Q3. TRANSCRIPTS (the existing corpus uses FMP)")
    print("=" * 78)
    # Current name
    status, body = _fetch("/stable/earning-call-transcript?symbol=AAPL&year=2023&quarter=2", key)
    if isinstance(body, list) and body:
        entry = body[0]
        if isinstance(entry, dict):
            content_len = len(entry.get("content") or "")
            print(
                f"  AAPL 2023 Q2: {status}  "
                f"date={entry.get('date')}  "
                f"period={entry.get('period')}  "
                f"len(content)={content_len}"
            )
            preview = (entry.get("content") or "")[:140]
            print(f"    preview: {preview!r}")
    else:
        print(f"  AAPL 2023 Q2: {status}  {_truncate(body)}")

    # Try a transcript for a name that became delisted (Lehman pre-BK)
    print("\n--- transcripts for known delisted name (Lehman 2008) ---")
    status, body = _fetch("/stable/earning-call-transcript?symbol=LEH&year=2008&quarter=2", key)
    if isinstance(body, list) and body:
        entry = body[0]
        if isinstance(entry, dict):
            content_len = len(entry.get("content") or "")
            print(
                f"  LEH 2008 Q2: {status}  "
                f"date={entry.get('date')}  "
                f"period={entry.get('period')}  "
                f"len(content)={content_len}"
            )
            preview = (entry.get("content") or "")[:140]
            print(f"    preview: {preview!r}")
    else:
        print(f"  LEH 2008 Q2: {status}  {_truncate(body)}")


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def main() -> None:
    key = _load_key()
    print(f"[..] key fingerprint: {_mask(key)}")
    status, body = _fetch("/stable/profile?symbol=AAPL", key)
    print(f"[..] AAPL profile (stable): status {status}")
    if status != 200:
        print(f"      body: {_truncate(body)}")
        sys.exit("FMP /stable/ auth failed; check FMP_API_KEY")
    print("[ok ] auth working against /stable/")

    smoke_delisted(key)
    smoke_delisted_list(key)
    smoke_pit_fundamentals(key)
    smoke_transcripts(key)

    print()
    print("=" * 78)
    print(" Done.")
    print("=" * 78)


if __name__ == "__main__":
    main()
