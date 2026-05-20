"""Tiny replay smoke test — 5 (ticker, decision_date) pairs.

Verifies the replay orchestrator end-to-end without running up an
LLM bill. Picks 5 widely-spaced (ticker, date) pairs from the test
universe, runs them through the RealLlmAgent, persists each Contract,
and prints the result.

Use scripts/run_replay_full.py for the larger replay run.

Run:
    uv run --env-file .env python scripts/run_replay_tiny.py
"""

import os
from datetime import date
from pathlib import Path

import psycopg

from fingym.agents.real_agent import RealLlmAgent
from fingym.agents.replay import ReplayItem, run_replay
from fingym.data.queries.contracts import count_by_signal_class, count_contracts
from fingym.llm.anthropic import AnthropicClient


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


_load_env_file(Path(__file__).resolve().parent.parent / ".env")

# 5 hand-picked pairs spanning sectors + the delisting test cases
TINY_REPLAY: list[ReplayItem] = [
    ReplayItem(ticker="AAPL", decision_date=date(2024, 3, 1)),
    ReplayItem(ticker="JPM", decision_date=date(2024, 6, 1)),
    ReplayItem(ticker="NVDA", decision_date=date(2023, 9, 1)),
    ReplayItem(ticker="SIVB", decision_date=date(2023, 2, 1)),  # 5 weeks before collapse
    ReplayItem(ticker="TWTR", decision_date=date(2022, 9, 1)),  # 2 months before go-private
]


def main() -> None:
    client = AnthropicClient(temperature=0.0)
    agent = RealLlmAgent(client=client, horizon_days=30)

    print(f"Tiny replay smoke test — {len(TINY_REPLAY)} (ticker, date) pairs")
    print()

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        before = count_contracts(conn)
        print(f"Contracts before: {before}")
        print()

        print("Running replay...")
        result = run_replay(conn, agent, TINY_REPLAY, progress_every=1)

        after = count_contracts(conn)
        print()
        print(f"Contracts after:  {after}")
        print(
            f"  attempted={result.attempted} succeeded={result.succeeded} "
            f"failed={result.failed} skipped_existing={result.skipped_existing}"
        )
        print(f"  elapsed: {result.elapsed_seconds():.1f}s")

        if result.failures:
            print("\nFailures:")
            for item, msg in result.failures:
                print(f"  {item.ticker} {item.decision_date}: {msg}")

        print("\nContracts by signal class:")
        for sci, n in count_by_signal_class(conn):
            print(f"  {sci:<50} n={n}")


if __name__ == "__main__":
    main()
