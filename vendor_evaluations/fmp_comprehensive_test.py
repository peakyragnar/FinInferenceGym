"""FMP /stable/ comprehensive evaluation.

Deeper than the smoke test. Verifies architecture-critical questions
before committing FMP as the primary data vendor. Runs against the
highest-tier subscription.

Three sections:

  1. ENDPOINT DISCOVERY: probe ~35 plausible /stable/ paths to map the
     subscription's surface area.

  2. ARCHITECTURE-CRITICAL DEEP TESTS:
       a. GE 2017 numbers-tie test (normalized vs as-reported revenue +
          net income; Michael's prior concern that restatements
          "didn't add up").
       b. Delisted-companies registry depth (paginate to find 2008-era
          delistings: Lehman, Enron, Bear Stearns, WaMu, MF Global).
       c. Search by company name for known delisted entities (alternative
          lookup path when historical tickers no longer resolve).
       d. SEC filings endpoint behaviour (filing-date access for PIT
          discipline cross-reference).
       e. Transcript coverage breadth (active vs delisted; year range).
       f. Macro and economic indicators coverage.

  3. SUMMARY: aggregate the findings.

Reads FMP_API_KEY from .env. Never prints the key. Run:

    uv run python vendor_evaluations/fmp_comprehensive_test.py
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
            return line.split("=", 1)[1].strip().strip("'\"")
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
        with urllib.request.urlopen(req, timeout=25) as resp:
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


def _truncate(value: Any, limit: int = 180) -> str:
    s = repr(value)
    return s if len(s) <= limit else s[:limit] + "..."


# ---------------------------------------------------------------------------
# Phase 1: endpoint discovery.
# ---------------------------------------------------------------------------


ENDPOINT_PROBES: list[tuple[str, str]] = [
    # Fundamentals (normalized)
    ("fundamentals:income-statement", "/stable/income-statement?symbol=AAPL&limit=1"),
    ("fundamentals:balance-sheet", "/stable/balance-sheet-statement?symbol=AAPL&limit=1"),
    ("fundamentals:cash-flow", "/stable/cash-flow-statement?symbol=AAPL&limit=1"),
    # Fundamentals (as-reported, PIT-pure)
    ("fundamentals:income-as-reported", "/stable/income-statement-as-reported?symbol=AAPL&limit=1"),
    (
        "fundamentals:balance-as-reported",
        "/stable/balance-sheet-statement-as-reported?symbol=AAPL&limit=1",
    ),
    (
        "fundamentals:cash-flow-as-reported",
        "/stable/cash-flow-statement-as-reported?symbol=AAPL&limit=1",
    ),
    # Derived ratios + metrics
    ("metrics:key-metrics", "/stable/key-metrics?symbol=AAPL&limit=1"),
    ("metrics:ratios", "/stable/ratios?symbol=AAPL&limit=1"),
    ("metrics:financial-growth", "/stable/financial-growth?symbol=AAPL&limit=1"),
    ("metrics:enterprise-values", "/stable/enterprise-values?symbol=AAPL&limit=1"),
    # Market data
    (
        "price:eod-light",
        "/stable/historical-price-eod/light?symbol=AAPL&from=2024-01-02&to=2024-01-05",
    ),
    (
        "price:eod-full",
        "/stable/historical-price-eod/full?symbol=AAPL&from=2024-01-02&to=2024-01-05",
    ),
    (
        "price:eod-div-adjusted",
        "/stable/historical-price-eod/dividend-adjusted?symbol=AAPL&from=2024-01-02&to=2024-01-05",
    ),
    ("price:quote", "/stable/quote?symbol=AAPL"),
    (
        "price:intraday-1min",
        "/stable/historical-chart/1min?symbol=AAPL&from=2024-01-02&to=2024-01-02",
    ),
    # Filings
    ("filings:sec-filings", "/stable/sec-filings?symbol=AAPL&page=0&limit=5"),
    ("filings:sec-by-type", "/stable/sec-filings-by-type?symbol=AAPL&type=10-K&page=0&limit=5"),
    ("filings:sec-financials", "/stable/sec-filings-financials?symbol=AAPL&page=0&limit=5"),
    # Transcripts
    ("transcripts:single", "/stable/earning-call-transcript?symbol=AAPL&year=2023&quarter=2"),
    ("transcripts:dates", "/stable/earning-call-transcript-dates?symbol=AAPL"),
    ("transcripts:latest", "/stable/earning-call-transcripts-latest?page=0&limit=5"),
    # Delisted / search
    ("registry:delisted", "/stable/delisted-companies?limit=5"),
    ("search:by-symbol", "/stable/search-symbol?query=AAPL"),
    ("search:by-name", "/stable/search-name?query=Apple"),
    ("search:by-cik", "/stable/search-cik?cik=0000320193"),
    # Ownership + analysts
    ("ownership:insider-trading", "/stable/insider-trading-latest?page=0&limit=5"),
    ("ownership:institutional-ownership", "/stable/institutional-ownership?symbol=AAPL"),
    ("analyst:estimates", "/stable/analyst-estimates?symbol=AAPL&period=annual&limit=2"),
    ("analyst:upgrades-downgrades", "/stable/grades-historical?symbol=AAPL&limit=5"),
    ("analyst:price-target", "/stable/price-target-news?symbol=AAPL&page=0&limit=5"),
    ("analyst:earnings-surprises", "/stable/earnings-surprises?symbol=AAPL&limit=5"),
    # ETFs / funds
    ("etf:holdings", "/stable/etf-holdings?symbol=SPY"),
    # Macro
    ("macro:treasury-rates", "/stable/treasury-rates?from=2024-01-01&to=2024-01-15"),
    (
        "macro:economic-indicators",
        "/stable/economic-indicators?name=GDP&from=2022-01-01&to=2024-01-01",
    ),
    ("macro:economic-calendar", "/stable/economic-calendar?from=2024-01-01&to=2024-01-15"),
    # News
    ("news:stock", "/stable/news/stock?symbols=AAPL&limit=3"),
    ("news:press-releases", "/stable/news/press-releases?symbols=AAPL&limit=3"),
    # Options
    ("options:chain-stable", "/stable/options-chain?symbol=AAPL"),
    # Universe
    ("universe:stock-list", "/stable/stock-list"),
    ("universe:tradable-list", "/stable/available-traded-list"),
]


def phase1_endpoint_discovery(key: str) -> dict[str, int]:
    print("=" * 78)
    print(" PHASE 1. ENDPOINT DISCOVERY (subscription surface)")
    print("=" * 78)
    statuses: dict[str, int] = {}
    for label, path in ENDPOINT_PROBES:
        status, body = _fetch(path, key)
        statuses[label] = status
        if status == 200:
            if isinstance(body, list):
                summary = f"list[{len(body)}]"
            elif isinstance(body, dict):
                summary = f"dict({len(body)} keys: {list(body.keys())[:5]})"
            else:
                summary = _truncate(body, 80)
            print(f"  [200]   {label:<38}  {summary}")
        else:
            print(f"  [{status}]   {label:<38}  {_truncate(body, 120)}")
    return statuses


# ---------------------------------------------------------------------------
# Phase 2: architecture-critical deep tests.
# ---------------------------------------------------------------------------


def deep_a_numbers_tie(key: str) -> None:
    """GE 2017: do normalized fundamentals tie to as-reported?

    Michael's prior concern was that FMP's normalized fundamentals
    applied revisions but didn't account for them correctly. Compare
    revenue + net income + filingDate between the two endpoints.
    """
    print()
    print("=" * 78)
    print(" 2A. NUMBERS-TIE TEST — GE 2017 normalized vs as-reported")
    print("=" * 78)

    status, norm = _fetch("/stable/income-statement?symbol=GE&period=annual&limit=40", key)
    if not isinstance(norm, list):
        print(f"  normalized fetch failed: {status} {_truncate(norm)}")
        return
    print(f"  fetched {len(norm)} GE annual filings (normalized)")

    # Find GE 2017
    norm_2017 = next(
        (e for e in norm if isinstance(e, dict) and (e.get("date") or "").startswith("2017")),
        None,
    )
    if not norm_2017:
        # Try matching by fillingDate / fiscal-year alternative
        norm_2017 = next(
            (
                e
                for e in norm
                if isinstance(e, dict)
                and (
                    (e.get("filingDate") or "").startswith("2018")
                    or (e.get("filingDate") or "").startswith("2017")
                )
            ),
            None,
        )

    if norm_2017:
        print(f"\n  NORMALIZED GE 2017 (date={norm_2017.get('date')}):")
        for k in (
            "filingDate",
            "acceptedDate",
            "period",
            "calendarYear",
            "revenue",
            "netIncome",
            "operatingIncome",
            "totalAssets",
            "cik",
            "link",
            "finalLink",
        ):
            if k in norm_2017:
                print(f"      {k}: {norm_2017.get(k)}")
    else:
        print("  no GE 2017 in the normalized 40-filing window")

    # As-reported equivalent
    status, asrep = _fetch(
        "/stable/income-statement-as-reported?symbol=GE&period=annual&limit=40", key
    )
    if not isinstance(asrep, list):
        print(f"\n  as-reported fetch failed: {status} {_truncate(asrep)}")
        return
    print(f"\n  fetched {len(asrep)} GE annual filings (as-reported)")

    asrep_2017 = next(
        (e for e in asrep if isinstance(e, dict) and (e.get("date") or "").startswith("2017")),
        None,
    )
    if asrep_2017:
        print(f"\n  AS-REPORTED GE 2017 (date={asrep_2017.get('date')}):")
        print(f"      total fields: {len(asrep_2017)}")
        # Look for revenue + net income keys (the as-reported endpoint
        # returns raw XBRL line-item names which vary by company).
        for k in sorted(asrep_2017.keys()):
            if any(
                pat in k.lower()
                for pat in (
                    "revenue",
                    "netincome",
                    "operatingincome",
                    "totalassets",
                    "filingdate",
                    "accepteddate",
                    "period",
                    "date",
                )
            ):
                print(f"      {k}: {asrep_2017.get(k)}")
    else:
        print("  no GE 2017 in the as-reported 40-filing window")


def deep_b_delisted_depth(key: str) -> None:
    """Paginate /stable/delisted-companies to find 2008-era delistings."""
    print()
    print("=" * 78)
    print(" 2B. DELISTED REGISTRY DEPTH — search for 2008-era entries")
    print("=" * 78)

    all_entries: list[dict[str, Any]] = []
    page = 0
    while page < 50:  # up to 50 pages
        status, body = _fetch(f"/stable/delisted-companies?limit=100&page={page}", key)
        if not isinstance(body, list) or not body:
            print(f"  page {page}: status {status}, stopping ({_truncate(body, 80)})")
            break
        all_entries.extend(body)
        page += 1
        if len(body) < 100:
            print(f"  page {page - 1}: returned {len(body)} (< 100) -> last page")
            break
    print(f"\n  total entries paginated: {len(all_entries)}")

    if not all_entries:
        return

    # Sort by delistedDate ascending (oldest first)
    with_dates = [e for e in all_entries if e.get("delistedDate")]
    with_dates.sort(key=lambda x: x.get("delistedDate") or "9999")
    print(f"  entries with delistedDate: {len(with_dates)}")
    if with_dates:
        print(f"  oldest delistedDate: {with_dates[0].get('delistedDate')}")
        print(f"  newest delistedDate: {with_dates[-1].get('delistedDate')}")

    # Filter for 2008-era entries
    crisis_entries = [
        e for e in with_dates if (e.get("delistedDate") or "").startswith(("2008", "2009"))
    ]
    print(f"\n  2008-2009 delistings in registry: {len(crisis_entries)}")
    for e in crisis_entries[:10]:
        sym = repr(e.get("symbol"))
        name = (e.get("companyName") or "")[:50]
        print(f"    {sym:<10}  {name:<50}  delisted={e.get('delistedDate')}")

    # Look for specific bankruptcy-era names
    for needle in ("Lehman", "Enron", "Bear Stearns", "Washington Mutual", "MF Global"):
        matches = [e for e in all_entries if needle.lower() in (e.get("companyName") or "").lower()]
        if matches:
            print(f"\n  '{needle}' matches:")
            for m in matches:
                sym = repr(m.get("symbol"))
                cname = repr(m.get("companyName"))
                print(f"    {sym}  {cname}  delisted={m.get('delistedDate')}")
        else:
            print(f"  '{needle}': not found in registry")


def deep_c_search_delisted(key: str) -> None:
    """Search FMP by company name for known delisted entities."""
    print()
    print("=" * 78)
    print(" 2C. SEARCH BY NAME — alternative lookup for delisted entities")
    print("=" * 78)
    for query in ("Lehman", "Enron", "Bear Stearns", "Washington Mutual", "MF Global"):
        encoded = urllib.parse.quote(query)
        print(f"\n--- query: {query!r} ---")

        status, body = _fetch(f"/stable/search-symbol?query={encoded}", key)
        if isinstance(body, list):
            print(f"  search-symbol {status}: {len(body)} results")
            for r in body[:5]:
                if isinstance(r, dict):
                    sym = repr(r.get("symbol"))
                    rname = repr(r.get("name"))
                    print(f"    {sym:<14} {rname}  exchange={r.get('exchangeFullName')}")
        else:
            print(f"  search-symbol {status}: {_truncate(body)}")

        status, body = _fetch(f"/stable/search-name?query={encoded}", key)
        if isinstance(body, list):
            print(f"  search-name {status}: {len(body)} results")
            for r in body[:5]:
                if isinstance(r, dict):
                    sym = repr(r.get("symbol"))
                    rname = repr(r.get("name"))
                    print(f"    {sym:<14} {rname}  exchange={r.get('exchangeFullName')}")
        else:
            print(f"  search-name {status}: {_truncate(body)}")


def deep_d_sec_filings(key: str) -> None:
    """Probe the SEC filings endpoint for filing-date access."""
    print()
    print("=" * 78)
    print(" 2D. SEC FILINGS ENDPOINT — filing-date PIT cross-reference")
    print("=" * 78)
    status, body = _fetch("/stable/sec-filings-by-type?symbol=AAPL&type=10-K&page=0&limit=10", key)
    if isinstance(body, list):
        print(f"  status {status}: {len(body)} 10-K filings for AAPL")
        for entry in body[:5]:
            if isinstance(entry, dict):
                date_keys = [
                    k
                    for k in entry.keys()
                    if any(s in k.lower() for s in ("date", "filing", "accept", "period"))
                ]
                print(f"    keys: {sorted(entry.keys())[:10]}")
                for k in date_keys:
                    print(f"      {k}: {entry.get(k)}")
                break  # just show one
    else:
        print(f"  status {status}: {_truncate(body)}")


def deep_e_transcript_coverage(key: str) -> None:
    """Transcript coverage: active vs delisted; year range."""
    print()
    print("=" * 78)
    print(" 2E. TRANSCRIPT COVERAGE")
    print("=" * 78)
    # Active name
    status, body = _fetch("/stable/earning-call-transcript-dates?symbol=AAPL", key)
    if isinstance(body, list):
        years = sorted(
            {
                entry[1]
                if isinstance(entry, list) and len(entry) > 1
                else entry.get("year")
                if isinstance(entry, dict)
                else None
                for entry in body
                if entry
            }
        )
        years_clean = [y for y in years if y]
        print(f"  AAPL transcript dates {status}: {len(body)} entries")
        if years_clean:
            print(f"    year range: {min(years_clean)} - {max(years_clean)}")
        print(f"    raw sample: {body[:3]}")
    else:
        print(f"  AAPL transcript dates {status}: {_truncate(body)}")

    # Delisted name
    status, body = _fetch("/stable/earning-call-transcript-dates?symbol=LEH", key)
    if isinstance(body, list):
        print(f"\n  LEH transcript dates {status}: {len(body)} entries (Lehman pre-BK)")
    else:
        print(f"\n  LEH transcript dates {status}: {_truncate(body)}")

    # Test a Lehman transcript directly
    status, body = _fetch("/stable/earning-call-transcript?symbol=LEH&year=2008&quarter=1", key)
    if isinstance(body, list) and body:
        first = body[0]
        content_len = len(first.get("content") or "") if isinstance(first, dict) else "?"
        print(f"  LEH 2008 Q1 transcript: status {status}, content len={content_len}")
    else:
        print(f"  LEH 2008 Q1 transcript: {status}  {_truncate(body)}")


def deep_f_macro_breadth(key: str) -> None:
    """Macro indicators breadth."""
    print()
    print("=" * 78)
    print(" 2F. MACRO COVERAGE BREADTH")
    print("=" * 78)
    indicators = [
        "GDP",
        "CPI",
        "unemploymentRate",
        "federalFundsRate",
        "consumerSentiment",
        "industrialProductionTotalIndex",
        "retailSales",
        "30YearFixedRateMortgageAverage",
    ]
    for name in indicators:
        status, body = _fetch(
            f"/stable/economic-indicators?name={name}&from=2022-01-01&to=2024-01-01",
            key,
        )
        if isinstance(body, list):
            print(f"  {name:<40} status {status}, {len(body)} rows")
            if body and isinstance(body[0], dict):
                sample = body[0]
                print(f"      sample: date={sample.get('date')}, value={sample.get('value')}")
        else:
            print(f"  {name:<40} status {status}, {_truncate(body, 80)}")


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def main() -> None:
    key = _load_key()
    print(f"[..] key fingerprint: {_mask(key)}")
    status, _ = _fetch("/stable/profile?symbol=AAPL", key)
    if status != 200:
        sys.exit(f"FMP /stable/ auth failed; status {status}")
    print("[ok ] /stable/ auth verified")

    statuses = phase1_endpoint_discovery(key)

    deep_a_numbers_tie(key)
    deep_b_delisted_depth(key)
    deep_c_search_delisted(key)
    deep_d_sec_filings(key)
    deep_e_transcript_coverage(key)
    deep_f_macro_breadth(key)

    print()
    print("=" * 78)
    print(" SUMMARY")
    print("=" * 78)
    available = sum(1 for s in statuses.values() if s == 200)
    print(f"  endpoint discovery: {available}/{len(statuses)} returned 200")
    forbidden = [name for name, s in statuses.items() if s == 403]
    not_found = [name for name, s in statuses.items() if s == 404]
    if forbidden:
        print(f"  403 (tier-gated or legacy): {forbidden}")
    if not_found:
        print(f"  404 (path doesn't exist or wrong shape): {not_found}")


if __name__ == "__main__":
    main()
