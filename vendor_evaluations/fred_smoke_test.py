"""FRED smoke test — Phase 2 NEW vendor verification for headline observables
and macro emissions.

For every proposed series, verifies:
  - existence (✓/✗)
  - frequency (daily / weekly / monthly / quarterly)
  - history depth (earliest observation)
  - publication delay (last_updated minus latest observation date)
  - latest value

Plus an ALFRED PIT test on CPIAUCSL and PAYEMS for April 2020 — confirms
that FRED returns first-print values via realtime_start / realtime_end
parameters, which is load-bearing for Stone 24 PIT discipline on macro
emissions.

Reads FRED_API_KEY from .env. Never prints the key. Run:

    uv run python vendor_evaluations/fred_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
BASE = "https://api.stlouisfed.org/fred"


def _load_key() -> str:
    if not ENV_PATH.exists():
        sys.exit(f"missing .env at {ENV_PATH}")
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("FRED_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("FRED_API_KEY not present in .env")


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}...{key[-3:]} (len={len(key)})"


def _fetch(path: str, params: dict[str, str], key: str) -> tuple[int, Any]:
    full_params = {**params, "api_key": key, "file_type": "json"}
    query = urllib.parse.urlencode(full_params)
    url = f"{BASE}{path}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "fingym-fred-smoke/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            payload = json.loads(body) if body else None
        except Exception:
            payload = None
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


SERIES_BY_CATEGORY: dict[str, list[tuple[str, str]]] = {
    "Rates": [
        ("DFF", "Daily Federal Funds Rate"),
        ("FEDFUNDS", "Effective Federal Funds Rate (monthly avg)"),
        ("DGS3MO", "3-Month Treasury Constant Maturity"),
        ("DGS2", "2-Year Treasury Constant Maturity"),
        ("DGS5", "5-Year Treasury Constant Maturity"),
        ("DGS10", "10-Year Treasury Constant Maturity"),
        ("DGS30", "30-Year Treasury Constant Maturity"),
        ("T10Y2Y", "10Y minus 2Y Treasury Spread"),
    ],
    "Inflation expectations": [
        ("T5YIFR", "5Y 5Y Forward Breakeven"),
        ("T10YIE", "10Y Breakeven Inflation Rate"),
    ],
    "Credit spreads": [
        ("BAMLH0A0HYM2", "ICE BofA US High Yield OAS"),
        ("BAMLC0A0CM", "ICE BofA US Corporate OAS"),
    ],
    "Volatility": [
        ("VIXCLS", "CBOE VIX Close"),
    ],
    "FX": [
        ("DTWEXBGS", "Broad US Dollar Index (Goods + Services)"),
        ("DEXUSEU", "USD to Euro"),
        ("DEXJPUS", "Japanese Yen to USD"),
        ("DEXCHUS", "Chinese Yuan to USD"),
    ],
    "Commodities": [
        ("DCOILWTICO", "WTI Crude Oil"),
        ("DCOILBRENTEU", "Brent Crude Oil"),
        ("GOLDAMGBD228NLBM", "Gold Fixing AM (London)"),
        ("PCOPPUSDM", "Global Price of Copper (monthly)"),
    ],
    "Macro emissions - monthly": [
        ("CPIAUCSL", "CPI All Urban Consumers"),
        ("CPILFESL", "Core CPI (ex food, energy)"),
        ("PCEPI", "PCE Price Index"),
        ("PCEPILFE", "Core PCE Price Index"),
        ("PAYEMS", "All Employees, Total Nonfarm"),
        ("UNRATE", "Unemployment Rate"),
        ("INDPRO", "Industrial Production Index"),
        ("RSAFS", "Advance Retail Sales"),
        ("HOUST", "Housing Starts: Total"),
    ],
    "Macro emissions - quarterly": [
        ("GDPC1", "Real GDP (chained 2017 $)"),
    ],
    "Macro emissions - weekly": [
        ("ICSA", "Initial Jobless Claims"),
        ("CCSA", "Continued Jobless Claims"),
    ],
    "ISM (license-restricted on FRED)": [
        ("NAPM", "ISM Manufacturing PMI"),
        ("NAPMNMI", "ISM Non-Manufacturing PMI"),
    ],
    "Other macro": [
        ("WALCL", "Fed Balance Sheet (Total Assets, weekly)"),
        ("M2SL", "M2 Money Stock (monthly)"),
    ],
}


def _series_info(series_id: str, key: str) -> dict[str, Any] | None:
    status, payload = _fetch("/series", {"series_id": series_id}, key)
    if status != 200 or payload is None:
        return None
    seriess = payload.get("seriess") or []
    return seriess[0] if seriess else None


def _latest_observation(series_id: str, key: str) -> dict[str, Any] | None:
    status, payload = _fetch(
        "/series/observations",
        {"series_id": series_id, "sort_order": "desc", "limit": "1"},
        key,
    )
    if status != 200 or payload is None:
        return None
    obs = payload.get("observations") or []
    return obs[0] if obs else None


def _delay_days(last_updated: str, latest_obs_date: str) -> int | None:
    try:
        upd_date_str = last_updated.split(" ")[0]
        upd = datetime.strptime(upd_date_str, "%Y-%m-%d").date()
        obs = datetime.strptime(latest_obs_date, "%Y-%m-%d").date()
        return (upd - obs).days
    except Exception:
        return None


def test_coverage_and_freshness(key: str) -> dict[str, dict[str, Any]]:
    print("\n=== Test 1: Coverage, frequency, delay, history ===\n")
    header = (
        f"{'ID':<22} {'OK':<3} {'Freq':<12} {'Earliest':<12} "
        f"{'Latest_obs':<12} {'Last_updated':<22} {'Delay':<7} {'Value':<15}"
    )
    print(header)
    print("-" * len(header))

    results: dict[str, dict[str, Any]] = {}

    for category, series in SERIES_BY_CATEGORY.items():
        print(f"\n--- {category} ---")
        for series_id, _description in series:
            info = _series_info(series_id, key)
            if info is None:
                results[series_id] = {"ok": False}
                print(f"{series_id:<22} {'✗':<3} (not found / restricted)")
                continue

            latest = _latest_observation(series_id, key)
            latest_value = (latest or {}).get("value", "?")
            latest_date = (latest or {}).get("date", "?")

            freq = info.get("frequency_short", "?")
            earliest = info.get("observation_start", "?")
            last_updated = info.get("last_updated", "?")
            delay = _delay_days(last_updated, latest_date) if latest_date != "?" else None
            delay_str = f"{delay}d" if delay is not None else "?"

            results[series_id] = {
                "ok": True,
                "title": info.get("title"),
                "frequency": freq,
                "frequency_long": info.get("frequency"),
                "earliest": earliest,
                "latest_obs_date": latest_date,
                "last_updated": last_updated,
                "delay_days": delay,
                "latest_value": latest_value,
                "units": info.get("units_short"),
            }

            print(
                f"{series_id:<22} {'✓':<3} {freq:<12} {earliest:<12} "
                f"{latest_date:<12} {last_updated[:19]:<22} {delay_str:<7} {latest_value!s:<15}"
            )

    return results


def _pit_test_pair(key: str, series_id: str, observation_month: str, first_print_date: str) -> None:
    print(f"\n--- {series_id} for {observation_month} ---")

    # First-print: query with realtime window covering only the release day
    _, payload = _fetch(
        "/series/observations",
        {
            "series_id": series_id,
            "observation_start": observation_month,
            "observation_end": observation_month,
            "realtime_start": first_print_date,
            "realtime_end": first_print_date,
        },
        key,
    )
    fp_obs = ((payload or {}).get("observations") or []) if payload else []
    first_print = fp_obs[0]["value"] if fp_obs else "(none)"

    # Current revised value
    _, payload = _fetch(
        "/series/observations",
        {
            "series_id": series_id,
            "observation_start": observation_month,
            "observation_end": observation_month,
        },
        key,
    )
    cur_obs = ((payload or {}).get("observations") or []) if payload else []
    current = cur_obs[0]["value"] if cur_obs else "(none)"

    print(f"  First-print (as of {first_print_date}): {first_print}")
    print(f"  Current (latest revision):           {current}")
    revised = "YES" if first_print != current and first_print != "(none)" else "NO"
    print(f"  Revisions detected: {revised}")


def test_alfred_pit(key: str) -> None:
    print("\n\n=== Test 2: PIT discipline via ALFRED vintage ===\n")
    print("Load-bearing test: can we retrieve first-print values for macro emissions?")
    print("Equal first-print and current = series not revised (some aren't)")
    print("Differing values = ALFRED vintage works AND the series gets revised")

    _pit_test_pair(key, "CPIAUCSL", "2020-04-01", "2020-05-12")
    _pit_test_pair(key, "PAYEMS", "2020-04-01", "2020-05-08")


def main() -> None:
    key = _load_key()
    print(f"FRED smoke test — key {_mask(key)}")

    results = test_coverage_and_freshness(key)
    test_alfred_pit(key)

    print("\n\n=== Summary ===")
    ok = sum(1 for r in results.values() if r["ok"])
    total = len(results)
    print(f"Series available: {ok}/{total}")
    missing = [sid for sid, r in results.items() if not r["ok"]]
    if missing:
        print(f"Missing: {missing}")


if __name__ == "__main__":
    main()
