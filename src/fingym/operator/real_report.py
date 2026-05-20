"""Real-data operator report (Phase 2 NEW Step 5).

Reads the trajectory store (`contracts` table on Postgres) and renders a
text dashboard. Complements the existing `report` subcommand which reads
from the toy JSONL Scoreboard + memory YAMLs.

Sections:
  1. Trajectory store summary (total contracts, per-agent counts)
  2. Per-ticker activity (contract count, decision-date range, latest)
  3. Per-signal-class inventory (the categorizations the LLM invented)
  4. Recent contracts (most recent N decisions with key fields)

This is the audit surface for the operator (DESIGN.md #10): see what
the real AI Core has been forecasting, on what evidence, with what
self-tagged categorization. Per-signal-class reliability and Track C
attribution against the Baseline are subsequent steps once enough
Contracts have matured to horizon for realized-return scoring.
"""

from __future__ import annotations

from typing import Any

import psycopg


def print_real_report(conn: psycopg.Connection[Any]) -> None:
    """Print the trajectory-store report to stdout."""
    print("=" * 78)
    print(" FinInferenceGym — Trajectory Store Report (real Contracts)")
    print("=" * 78)

    total, by_agent, earliest, latest = _summary(conn)
    print(f"\n Contracts:    {total}")
    if earliest and latest:
        print(f" Decision range: {earliest.date()} → {latest.date()}")
    print(" Per-agent:")
    for agent_id, n in by_agent:
        print(f"   {agent_id:<24} {n:>6}")

    if total == 0:
        print("\n (no Contracts persisted yet; run scripts/run_replay_tiny.py)")
        return

    _print_per_ticker(conn)
    _print_per_signal_class(conn)
    _print_recent(conn)


def _summary(conn: psycopg.Connection[Any]) -> tuple[int, list[tuple[str, int]], Any, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), MIN(decision_time), MAX(decision_time) FROM contracts")
        row = cur.fetchone()
        total = int(row[0]) if row else 0
        earliest = row[1] if row else None
        latest = row[2] if row else None
        cur.execute("SELECT agent_id, COUNT(*) FROM contracts GROUP BY agent_id ORDER BY 2 DESC")
        by_agent = [(r[0], int(r[1])) for r in cur.fetchall()]
    return total, by_agent, earliest, latest


def _print_per_ticker(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [1] Per-ticker activity")
    print(" " + "-" * 76)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker,
                   COUNT(*) AS n,
                   MIN(decision_time::date) AS earliest,
                   MAX(decision_time::date) AS latest
            FROM contracts GROUP BY ticker
            ORDER BY ticker
            """
        )
        rows = cur.fetchall()
    if not rows:
        print("   (no contracts)")
        return
    print(f"   {'ticker':<8} {'n':>5}  {'earliest':<12} {'latest':<12}")
    for r in rows:
        print(f"   {r[0]:<8} {r[1]:>5}  {r[2]!s:<12} {r[3]!s:<12}")


def _print_per_signal_class(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [2] Per-signal-class inventory")
    print(" " + "-" * 76)
    print("     (each tag is a self-categorization the LLM chose at decision time;")
    print("      Forecast Ledger reliability per tag fills as Contracts mature to horizon)")
    print()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT signal_class_id,
                   COUNT(*) AS n,
                   STRING_AGG(DISTINCT ticker, ',' ORDER BY ticker) AS tickers
            FROM contracts GROUP BY signal_class_id
            ORDER BY n DESC, signal_class_id
            """
        )
        rows = cur.fetchall()
    if not rows:
        print("   (no contracts)")
        return
    print(f"   {'signal_class_id':<48} {'n':>5}  tickers")
    for r in rows:
        sci = r[0]
        n = r[1]
        tickers = r[2] or ""
        if len(sci) > 47:
            sci = sci[:44] + "..."
        print(f"   {sci:<48} {n:>5}  {tickers}")


def _print_recent(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [3] Recent Contracts (most recent 10 decisions)")
    print(" " + "-" * 76)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT decision_time, ticker, agent_id, signal_class_id,
                   recommended_action_type, recommended_expression, recommended_direction,
                   forecast_distribution
            FROM contracts
            ORDER BY decision_time DESC
            LIMIT 10
            """
        )
        rows = cur.fetchall()
    if not rows:
        print("   (no contracts)")
        return
    for r in rows:
        decision_time, ticker, agent_id, sci, action_type = r[0], r[1], r[2], r[3], r[4]
        expr, direction = r[5], r[6]
        dist = r[7]  # JSONB → dict
        print(f"   {decision_time.date()}  {ticker:<5}  {agent_id:<14}  {sci}")
        if action_type == "trade":
            print(f"     action: trade  {expr}  {direction}")
        else:
            print("     action: no_action")
        # Compact one-line forecast
        if isinstance(dist, dict):
            buckets = (
                "below_minus_5",
                "minus_5_to_0",
                "zero_to_plus_5",
                "plus_5_to_plus_10",
                "above_plus_10",
            )
            line = "     forecast: " + "  ".join(f"{b[:8]}={dist.get(b, 0.0):.2f}" for b in buckets)
            print(line)
        print()


__all__ = ["print_real_report"]
