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

from fingym.data.queries.forecast_ledger import (
    compute_reliability,
    realized_edge_per_agent,
)


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
    _print_realized_edge(conn)
    _print_reliability(conn)
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


def _print_realized_edge(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [3] Realized edge per agent (matured Contracts only)")
    print(" " + "-" * 76)
    print("     mean log return per Contract, direction-adjusted (long=+, short=-,")
    print("     no_action=0). Track C attribution is the difference between an")
    print("     AI agent's mean and the Baseline's mean on the same decision set.")
    print()
    rows = realized_edge_per_agent(conn)
    if not rows:
        print("   (no Contracts matured yet — none have decision_time + horizon < now)")
        return
    print(f"   {'agent_id':<28} {'n_matured':>10} {'mean_log_return':>16}")
    for agent_id, n, mean_log_ret in rows:
        pct = mean_log_ret * 100
        print(f"   {agent_id:<28} {n:>10} {pct:>14.2f}%")


def _print_reliability(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [4] Forecast Ledger reliability (per signal class and claim bin)")
    print(" " + "-" * 76)
    print("     each row: when this agent claimed X% on a return bucket under this")
    print("     signal_class_id, what fraction of those claims actually realized.")
    print("     A perfectly calibrated agent has observed_rate ≈ mean_claim.")
    print()
    rows = compute_reliability(conn)
    if not rows:
        print("   (no matured Contracts yet — reliability fills as horizons elapse)")
        return
    print(
        f"   {'signal_class_id':<36} {'agent':<24} "
        f"{'bin':>10} {'mean_claim':>10} {'observed':>9} {'n':>5}"
    )
    for r in rows:
        sci = r.signal_class_id
        if len(sci) > 35:
            sci = sci[:32] + "..."
        ag = r.agent_id
        if len(ag) > 23:
            ag = ag[:20] + "..."
        bin_str = f"[{r.claim_bin_lo:.2f},{r.claim_bin_hi:.2f})"
        print(
            f"   {sci:<36} {ag:<24} "
            f"{bin_str:>10} {r.mean_claim:>10.3f} {r.observed_rate:>9.3f} {r.count:>5}"
        )


def _print_recent(conn: psycopg.Connection[Any]) -> None:
    print()
    print(" [5] Recent Contracts (most recent 10 decisions)")
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
