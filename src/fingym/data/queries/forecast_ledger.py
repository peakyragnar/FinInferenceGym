"""Forecast Ledger reliability — empirical truth rate per signal class.

The architectural commitment from DESIGN.md #2 + PYRAMID Stone 11b:
the Forecast Ledger tracks, per (agent, signal_class_id), what fraction
of forecasts that claimed X% confidence on bucket B realized B in fact.
The promotion gate + the Action Engine's calibration shrinkage both read
this view.

Procedure:
  1. Pull every Contract from the trajectory store
  2. For each Contract whose decision_time + horizon has elapsed,
     compute the realized return at horizon via equity_returns query
  3. Bucket the realized return into the 5-bucket scheme
  4. Pair the Contract's claim per bucket with the actually-observed
     realized bucket (1 if matched, 0 if not)
  5. Aggregate by (signal_class_id, claim_bin): mean_claim, observed_rate, count

`horizon_days` is parsed from the Contract's `horizon` field (e.g.,
"30d" → 30). Contracts whose horizon hasn't matured yet are skipped.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg

from fingym.data.queries.equity_returns import (
    RETURN_BUCKETS,
    bucket_for_log_return,
)

# Claim-bucket bins for reliability aggregation. Standard 10-bin uniform.
CLAIM_BINS: tuple[tuple[float, float], ...] = (
    (0.00, 0.10),
    (0.10, 0.20),
    (0.20, 0.30),
    (0.30, 0.40),
    (0.40, 0.50),
    (0.50, 0.60),
    (0.60, 0.70),
    (0.70, 0.80),
    (0.80, 0.90),
    (0.90, 1.001),
)


@dataclass(frozen=True)
class ReliabilityRow:
    """One row of per-signal-class reliability.

    For (signal_class_id, claim_bin), the agent has made `count` claims
    in that bin. `mean_claim` is the average probability they assigned;
    `observed_rate` is the empirical fraction of those claims where the
    realized bucket actually matched.
    """

    signal_class_id: str
    agent_id: str
    claim_bin_lo: float
    claim_bin_hi: float
    mean_claim: float
    observed_rate: float
    count: int


def _parse_horizon_days(horizon: str) -> int | None:
    """Parse '30d' / '1m' / '3m' / etc. into days. Returns None if unparseable."""
    s = horizon.strip().lower()
    if s.endswith("d"):
        try:
            return int(s[:-1])
        except ValueError:
            return None
    if s.endswith("m"):
        try:
            return int(s[:-1]) * 30
        except ValueError:
            return None
    if s.endswith("y"):
        try:
            return int(s[:-1]) * 365
        except ValueError:
            return None
    return None


def _bin_for_claim(p: float) -> tuple[float, float] | None:
    """Map a probability to its claim bin (lo, hi). None if out of range."""
    for lo, hi in CLAIM_BINS:
        if lo <= p < hi:
            return (lo, hi)
    return None


def _close_on_or_after(
    conn: psycopg.Connection[Any], ticker: str, target: date
) -> tuple[date, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of, close FROM equity_prices
            WHERE ticker = %s AND as_of >= %s AND close IS NOT NULL
            ORDER BY as_of ASC LIMIT 1
            """,
            (ticker, target),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else None


def compute_reliability(
    conn: psycopg.Connection[Any],
    agent_id: str | None = None,
    as_of_time: datetime | None = None,
) -> list[ReliabilityRow]:
    """Compute the Forecast Ledger reliability view.

    Optional agent_id filter (None = all agents). `as_of_time` is the
    cutoff for considering Contracts ready to score (their decision_time
    + horizon must be <= as_of_time). Default is now (UTC).

    Returns rows ordered by (signal_class_id, claim_bin_lo)."""
    if as_of_time is None:
        as_of_time = datetime.now(UTC)

    # Pull candidate Contracts with their forecast distributions
    sql = """
        SELECT contract_id, decision_time, ticker, horizon, signal_class_id,
               agent_id, forecast_distribution
        FROM contracts
        """
    params: list[Any] = []
    if agent_id is not None:
        sql += " WHERE agent_id = %s"
        params.append(agent_id)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    # counts[(signal_class_id, agent_id, bin_lo, bin_hi)] = (sum_claims, hits, n)
    counts: dict[tuple[str, str, float, float], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])

    for row in rows:
        _cid, decision_time, ticker, horizon_str, sci, row_agent, dist = row
        days = _parse_horizon_days(horizon_str)
        if days is None:
            continue
        horizon_target = decision_time + timedelta(days=days)
        if horizon_target > as_of_time:
            continue  # Horizon not yet matured

        # Compute realized return
        start = _close_on_or_after(conn, ticker, decision_time.date())
        if start is None:
            continue
        end = _close_on_or_after(conn, ticker, decision_time.date() + timedelta(days=days))
        if end is None:
            continue
        start_close = float(start[1])
        end_close = float(end[1])
        if start_close <= 0 or end_close <= 0:
            continue
        import math

        log_ret = math.log(end_close / start_close)
        realized = bucket_for_log_return(log_ret)

        # Expand the forecast distribution into per-bucket claims
        if not isinstance(dist, dict):
            continue
        for bucket in RETURN_BUCKETS:
            claim = dist.get(bucket)
            if not isinstance(claim, int | float):
                continue
            p = float(claim)
            bin_ = _bin_for_claim(p)
            if bin_ is None:
                continue
            key = (sci, row_agent, bin_[0], bin_[1])
            hit = 1.0 if bucket == realized else 0.0
            counts[key][0] += p
            counts[key][1] += hit
            counts[key][2] += 1

    # Build rows
    out: list[ReliabilityRow] = []
    for (sci, ag, lo, hi), (sum_claims, hits, n) in counts.items():
        if n <= 0:
            continue
        out.append(
            ReliabilityRow(
                signal_class_id=sci,
                agent_id=ag,
                claim_bin_lo=lo,
                claim_bin_hi=hi,
                mean_claim=sum_claims / n,
                observed_rate=hits / n,
                count=int(n),
            )
        )
    out.sort(key=lambda r: (r.signal_class_id, r.agent_id, r.claim_bin_lo))
    return out


def realized_edge_per_agent(
    conn: psycopg.Connection[Any],
    as_of_time: datetime | None = None,
) -> list[tuple[str, int, float]]:
    """Per-agent realized log-return summary — basis for Track C attribution.

    Returns (agent_id, n_matured_contracts, mean_log_return). Mean log return
    is computed across all Contracts whose horizon has matured, weighted by
    direction (long = +, short = -, no_action = 0).
    """
    if as_of_time is None:
        as_of_time = datetime.now(UTC)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT contract_id, decision_time, ticker, horizon, agent_id,
                   recommended_action_type, recommended_direction
            FROM contracts
            """,
        )
        rows = cur.fetchall()

    bucket: dict[str, list[float]] = defaultdict(list)
    import math

    for row in rows:
        _cid, decision_time, ticker, horizon_str, ag, action_type, direction = row
        days = _parse_horizon_days(horizon_str)
        if days is None:
            continue
        if decision_time + timedelta(days=days) > as_of_time:
            continue

        # No-action contracts contribute 0 (no P&L attempted)
        if action_type != "trade":
            bucket[ag].append(0.0)
            continue

        start = _close_on_or_after(conn, ticker, decision_time.date())
        if start is None:
            continue
        end = _close_on_or_after(conn, ticker, decision_time.date() + timedelta(days=days))
        if end is None:
            continue
        start_close = float(start[1])
        end_close = float(end[1])
        if start_close <= 0 or end_close <= 0:
            continue
        log_ret = math.log(end_close / start_close)
        if direction == "short":
            log_ret = -log_ret
        bucket[ag].append(log_ret)

    out: list[tuple[str, int, float]] = []
    for ag, vals in bucket.items():
        if not vals:
            continue
        out.append((ag, len(vals), sum(vals) / len(vals)))
    out.sort(key=lambda x: -x[2])
    return out
