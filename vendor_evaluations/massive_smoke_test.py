"""Massive (Polygon) API smoke test for Phase 1 vendor evaluation.

Verifies two architecture-critical properties before we commit to Massive
as the primary data vendor:

  1. DELISTED COVERAGE — does the API return historical data for stocks
     that went to zero / were acquired / went bankrupt? Survivorship
     mitigation requires yes (BUILD.md Phase 1 slippage watch).

  2. POINT-IN-TIME (PIT) FUNDAMENTALS — does the financials endpoint
     expose the data as it was originally reported, with `filing_date`
     and / or revision-tracking, or only the latest restated values?

Reads `MASSIVE_API_KEY` from .env. Never prints the key. Run:

    uv run python vendor_evaluations/massive_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Setup — load API key, pick a working base URL.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"


def _load_key() -> str:
    if not ENV_PATH.exists():
        sys.exit(f"missing .env at {ENV_PATH}")
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("MASSIVE_API_KEY="):
            value = line.split("=", 1)[1].strip()
            return value.strip("'\"")
    sys.exit("MASSIVE_API_KEY not present in .env")


def _fetch(url: str) -> tuple[int, dict[str, Any] | str]:
    """GET and return (status, parsed_json_or_body_text). Never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": "fingym-smoke/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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


def _fetch_with_auth(
    base: str, path: str, key: str, auth_method: str
) -> tuple[int, dict[str, Any] | str]:
    """Fetch base+path using the chosen auth method.

    auth_method is one of:
      - "query"   -> append ?apiKey=KEY to the URL
      - "bearer"  -> Authorization: Bearer KEY header
    """
    sep = "&" if "?" in path else "?"
    if auth_method == "query":
        url = f"{base}{path}{sep}apiKey={key}"
        headers = {"User-Agent": "fingym-smoke/0.1"}
    elif auth_method == "bearer":
        url = f"{base}{path}"
        headers = {
            "User-Agent": "fingym-smoke/0.1",
            "Authorization": f"Bearer {key}",
        }
    else:
        raise ValueError(f"unknown auth_method {auth_method}")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}...{key[-3:]} (len={len(key)})"


def _detect_base_and_auth(key: str) -> tuple[str, str]:
    """Find a (base, auth_method) combo that returns 200 on AAPL ref.

    Tries (polygon, massive) x (query, bearer). On 4xx, prints the body so
    the server's error message is visible.
    """
    print(f"[..] key fingerprint: {_mask(key)}")
    bases = ["https://api.polygon.io", "https://api.massive.com"]
    auths = ["query", "bearer"]
    for base in bases:
        for auth in auths:
            status, body = _fetch_with_auth(base, "/v3/reference/tickers/AAPL", key, auth)
            print(f"[..] base={base}  auth={auth}  -> status {status}")
            if status >= 400:
                print(f"      body: {_truncate(body, 220)}")
            if status == 200:
                print(f"[ok ] using base={base}  auth={auth}")
                return base, auth
    sys.exit("no working (base, auth) combination found")


# ---------------------------------------------------------------------------
# Smoke checks.
# ---------------------------------------------------------------------------


# Pre-bankruptcy tickers (the names used during normal trading, not the
# BK proceedings tickers with the 'Q' suffix). A survivorship-conscious
# dataset should retain these.
DELISTED_TICKERS = [
    ("LEH", "Lehman Brothers (pre-BK)", "2008-08-01", "2008-09-15"),
    ("ENE", "Enron (pre-BK, NYSE)", "2001-10-01", "2001-11-30"),
    ("BSC", "Bear Stearns (pre-JPM)", "2008-02-01", "2008-03-17"),
    ("WM", "Washington Mutual (pre-BK)", "2008-08-01", "2008-09-26"),
    ("MF", "MF Global (pre-BK)", "2011-09-01", "2011-10-31"),
]


def _truncate(value: Any, limit: int = 200) -> str:
    s = repr(value)
    return s if len(s) <= limit else s[:limit] + "..."


def smoke_delisted(base: str, key: str, auth: str) -> None:
    print()
    print("=" * 78)
    print(" Q1. DELISTED COVERAGE")
    print("=" * 78)
    for ticker, name, from_date, to_date in DELISTED_TICKERS:
        print(f"\n--- {ticker} ({name}) ---")

        # Reference (does the ticker even resolve?)
        status, body = _fetch_with_auth(base, f"/v3/reference/tickers/{ticker}", key, auth)
        print(f"  ref {status}: {_truncate(body)}")

        # Historical daily aggregates around the demise window.
        status, body = _fetch_with_auth(
            base,
            f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}",
            key,
            auth,
        )
        if isinstance(body, dict):
            result_count = body.get("resultsCount") or len(body.get("results") or [])
            print(f"  aggs {status} ({from_date} -> {to_date}): {result_count} bars")
            sample = (body.get("results") or [])[:2]
            for bar in sample:
                print(f"      {bar}")
        else:
            print(f"  aggs {status}: {_truncate(body)}")

        # Reference financials, if available (vX path on Polygon).
        status, body = _fetch_with_auth(
            base, f"/vX/reference/financials?ticker={ticker}&limit=3", key, auth
        )
        if isinstance(body, dict):
            count = len(body.get("results") or [])
            print(f"  financials vX {status}: {count} filings returned")
            if count > 0:
                first = (body.get("results") or [None])[0]
                if isinstance(first, dict):
                    keys = list(first.keys())[:12]
                    print(f"      first filing keys: {keys}")
        else:
            print(f"  financials vX {status}: {_truncate(body)}")


def smoke_pit_fundamentals(base: str, key: str, auth: str) -> None:
    print()
    print("=" * 78)
    print(" Q2. PIT FUNDAMENTALS SHAPE")
    print("=" * 78)
    # GE: had visible restatement events in 2017/2018. We pull multiple
    # filings for the same fiscal period and inspect their dates / version
    # fields, if any.
    path = (
        "/vX/reference/financials"
        "?ticker=GE&period_of_report_date.gte=2017-01-01"
        "&period_of_report_date.lte=2017-12-31"
        "&limit=20"
    )
    status, body = _fetch_with_auth(base, path, key, auth)
    print(f"\nGE 2017 fundamentals: status {status}")
    if not isinstance(body, dict):
        print(f"  raw: {_truncate(body)}")
        return

    results = body.get("results") or []
    print(f"  results: {len(results)}")

    if not results:
        print("  no filings returned — fundamentals endpoint may be on a higher tier")
        return

    # Inspect the keys on the first result for PIT-relevant fields, BOTH
    # at top level AND inside the financials sub-object (which may carry
    # filing_date semantics).
    first = results[0]
    if isinstance(first, dict):
        top_keys = sorted(first.keys())
        print(f"  top-level keys on a filing: {top_keys}")

        # Top-level PIT-relevant fields.
        pit_top = [
            k
            for k in top_keys
            if any(
                s in k.lower()
                for s in (
                    "date",
                    "filed",
                    "filing",
                    "period",
                    "as_of",
                    "as_known",
                    "accept",
                    "publish",
                    "revision",
                    "version",
                )
            )
        ]
        print(f"  PIT-adjacent top-level fields: {pit_top}")
        for k in pit_top:
            print(f"    {k}: {first.get(k)}")

        # Deep-dive: examine the `financials` sub-object structure.
        fin = first.get("financials")
        if isinstance(fin, dict):
            section_names = sorted(fin.keys())
            print(f"  `financials` sub-object sections: {section_names}")
            # Sample one section's keys to see what per-line-item fields look like.
            for section_name in section_names[:1]:
                section = fin[section_name]
                if isinstance(section, dict):
                    item_names = sorted(section.keys())
                    print(f"    e.g. {section_name!r} has items: {item_names[:6]}")
                    for item_name in item_names[:1]:
                        item = section[item_name]
                        if isinstance(item, dict):
                            print(f"      e.g. {item_name!r} keys: {sorted(item.keys())}")

        # Are there multiple filings for the same period_of_report?
        by_period: dict[str, int] = {}
        for r in results:
            if isinstance(r, dict):
                period = r.get("period_of_report_date") or r.get("end_date") or "<unknown>"
                by_period[period] = by_period.get(period, 0) + 1
        print("  filings per period (>1 indicates restatements tracked):")
        for period, count in sorted(by_period.items()):
            marker = "  <-- multiple!" if count > 1 else ""
            print(f"    {period}: {count}{marker}")

        # If multiple filings exist for a period, show all their top-level keys
        # to see what distinguishes them.
        multi_periods = [p for p, c in by_period.items() if c > 1]
        for period in multi_periods:
            print(f"  --- multiple filings for {period}: ---")
            for r in results:
                if isinstance(r, dict) and (
                    r.get("period_of_report_date") == period or r.get("end_date") == period
                ):
                    distinguish = {
                        k: r.get(k)
                        for k in (
                            "fiscal_period",
                            "fiscal_year",
                            "timeframe",
                            "filing_date",
                            "filed_at",
                            "acceptance_datetime",
                        )
                        if k in r
                    }
                    print(f"    {distinguish}")


def smoke_macro(base: str, key: str, auth: str) -> None:
    print()
    print("=" * 78)
    print(" Q3. MACRO COVERAGE (quick check vs FRED replacement)")
    print("=" * 78)
    endpoints = [
        ("/fed/v1/treasury-yields", "Treasury yields"),
        ("/fed/v1/inflation", "Realized inflation"),
        ("/fed/v1/inflation-expectations", "Inflation expectations"),
    ]
    for path, label in endpoints:
        status, body = _fetch_with_auth(base, path, key, auth)
        if isinstance(body, dict):
            count = len(body.get("results") or [])
            print(f"  {label}: status {status}, {count} rows")
        else:
            print(f"  {label}: status {status}, {_truncate(body)}")


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def main() -> None:
    key = _load_key()
    base, auth = _detect_base_and_auth(key)
    smoke_delisted(base, key, auth)
    smoke_pit_fundamentals(base, key, auth)
    smoke_macro(base, key, auth)
    print()
    print("=" * 78)
    print(" Done. Inspect output above to decide:")
    print(" - delisted aggs return real bars across the bankruptcy window? -> coverage")
    print(" - financials response carries filing_date AND has multiple rows per fiscal")
    print("   period? -> PIT discipline.")
    print("=" * 78)


if __name__ == "__main__":
    main()
