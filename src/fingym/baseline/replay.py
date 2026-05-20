"""Train the RealMarketStateBaseline and emit Contracts on a set of
(ticker, decision_date) pairs.

Lives inside src/fingym/baseline/ because the architectural import
boundary (mechanisms/lints/no_baseline_imports.py) forbids importing
`fingym.baseline` from anywhere outside this package (the AI Core never
sees the Baseline's processed forecast — PYRAMID Stone 11e). Operational
orchestration that wires the Baseline to the trajectory store must
live INSIDE the package.

Run:
    uv run --env-file .env python -m fingym.baseline.replay
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import psycopg

from fingym.baseline.real_baseline_agent import RealBaselineAgent
from fingym.baseline.training import TEST_UNIVERSE, train_baseline
from fingym.data.queries.contracts import count_contracts, save_contract


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


# Same 5 (ticker, date) pairs as scripts/run_replay_tiny.py uses for the
# AI Core, so the Track C comparison is on identical decisions.
DEFAULT_PAIRS: list[tuple[str, date]] = [
    ("AAPL", date(2024, 3, 1)),
    ("JPM", date(2024, 6, 1)),
    ("NVDA", date(2023, 9, 1)),
    ("SIVB", date(2023, 2, 1)),
    ("TWTR", date(2022, 9, 1)),
]

DEFAULT_HORIZON_DAYS = 30


def main() -> int:
    _load_env_file(Path(__file__).resolve().parents[3] / ".env")

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2

    horizon = int(os.environ.get("BASELINE_HORIZON_DAYS", DEFAULT_HORIZON_DAYS))
    pairs = DEFAULT_PAIRS

    print(f"Training the Baseline on {len(TEST_UNIVERSE)} tickers, horizon={horizon}d")
    print()
    with psycopg.connect(db_url) as conn:
        baseline = train_baseline(conn, TEST_UNIVERSE, horizon)
        print()
        print(f"Trained: cells={baseline.cells_populated()} obs={baseline.total_observations()}")
        print()

        agent = RealBaselineAgent(baseline=baseline, horizon_days=horizon)

        before = count_contracts(conn)
        print(f"Contracts before: {before}")
        print(f"Running Baseline on {len(pairs)} pairs...")
        print()

        succeeded = 0
        for ticker, decision_date in pairs:
            try:
                contract = agent.forecast_for(conn, ticker, decision_date)
                save_contract(conn, contract, ticker)
                conn.commit()
                top_bucket = max(
                    contract.forecast_distribution.probabilities.items(), key=lambda x: x[1]
                )
                action = contract.recommended_action.action_type
                if action == "trade":
                    action_str = f"trade {contract.recommended_action.direction}"  # type: ignore[union-attr]
                else:
                    action_str = "no_action"
                print(
                    f"  {ticker:<5} {decision_date}  sci={contract.signal_class_id}  "
                    f"top={top_bucket[0]}({top_bucket[1]:.2f})  {action_str}"
                )
                succeeded += 1
            except Exception as e:
                print(f"  {ticker} {decision_date}: FAILED — {type(e).__name__}: {e}")
                conn.rollback()

        after = count_contracts(conn)
        print()
        print(f"Contracts after:  {after}  (+{after - before}; succeeded {succeeded}/{len(pairs)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
