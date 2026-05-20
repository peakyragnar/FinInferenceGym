"""Trajectory store I/O — save and load Contract objects to/from Postgres.

The contracts table (migration d3f9c47b2a01) holds the trajectory store
from DESIGN.md #8: every forecast preserved with full provenance, in
SFT-fit format for year-2 own-model training.

Denormalized scalar columns enable fast aggregation queries (per ticker,
per signal class, per agent, per horizon). The full Contract is also
stored as JSONB for round-trip via pydantic.

Ticker is a SEPARATE argument to save_contract because the v5 Contract
schema has no top-level ticker field — it's implicit in the action's
underlying (for TradeAction) or in the evidence refs. We pass it
explicitly to keep the denormalized column populated for NoAction too.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import psycopg

from fingym.agents.contract import Contract, NoAction, TradeAction


def _contract_to_jsonable(contract: Contract) -> dict[str, Any]:
    """Convert Contract to JSON-serializable dict via pydantic's model_dump.
    Datetime values are isoformatted; we use mode='json' for stable serialization."""
    return contract.model_dump(mode="json")


def save_contract(conn: psycopg.Connection[Any], contract: Contract, ticker: str) -> None:
    """Persist one Contract to the contracts table.

    `ticker` is denormalized (the Contract schema has no top-level ticker
    field — it's implicit in evidence + action). Idempotent on
    contract_id (re-saving the same contract is a no-op via ON CONFLICT).
    """
    action = contract.recommended_action
    action_type = action.action_type
    if isinstance(action, TradeAction):
        expression: str | None = action.expression_type
        direction: str | None = action.direction
        underlying: str | None = action.underlying
        no_action_reason: str | None = None
    elif isinstance(action, NoAction):
        expression = None
        direction = None
        underlying = None
        no_action_reason = action.reason
    else:
        raise ValueError(f"Unexpected action type: {type(action).__name__}")

    contract_json = _contract_to_jsonable(contract)
    forecast_json = dict(contract.forecast_distribution.probabilities)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO contracts (
                contract_id, decision_time, agent_id, model_id, prompt_version,
                ticker, horizon, signal_class_id, thesis_category,
                recommended_action_type, recommended_size,
                recommended_expression, recommended_direction, recommended_underlying,
                no_action_reason, forecast_distribution, contract_json,
                data_sources_used
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (contract_id) DO NOTHING
            """,
            (
                contract.contract_id,
                contract.decision_time,
                contract.agent_id,
                contract.model_id,
                contract.prompt_version,
                ticker,
                contract.horizon,
                contract.signal_class_id,
                contract.thesis_category,
                action_type,
                Decimal(str(contract.recommended_size)),
                expression,
                direction,
                underlying,
                no_action_reason,
                json.dumps(forecast_json),
                json.dumps(contract_json),
                list(contract.data_sources_used),
            ),
        )


def load_contract(conn: psycopg.Connection[Any], contract_id: str) -> Contract | None:
    """Load one Contract by ID via round-trip from contract_json."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT contract_json FROM contracts WHERE contract_id = %s",
            (contract_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return Contract.model_validate(row[0])


def count_contracts(conn: psycopg.Connection[Any]) -> int:
    """Total Contracts persisted (diagnostic)."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM contracts")
        row = cur.fetchone()
    return int(row[0]) if row else 0


def list_recent_contracts(
    conn: psycopg.Connection[Any],
    ticker: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent Contracts (denormalized fields) for inspection.

    Returns dicts ordered by decision_time descending. Optional ticker
    filter. Does NOT load the full Contract — use load_contract for that.
    """
    sql = """
        SELECT contract_id, decision_time, agent_id, ticker, horizon,
               signal_class_id, thesis_category,
               recommended_action_type, recommended_expression,
               recommended_direction, forecast_distribution
        FROM contracts
    """
    params: tuple[Any, ...] = ()
    if ticker is not None:
        sql += " WHERE ticker = %s"
        params = (ticker,)
    sql += " ORDER BY decision_time DESC LIMIT %s"
    params = (*params, limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "contract_id": r[0],
                "decision_time": r[1],
                "agent_id": r[2],
                "ticker": r[3],
                "horizon": r[4],
                "signal_class_id": r[5],
                "thesis_category": r[6],
                "recommended_action_type": r[7],
                "recommended_expression": r[8],
                "recommended_direction": r[9],
                "forecast_distribution": r[10],
            }
        )
    return out


def count_by_signal_class(
    conn: psycopg.Connection[Any],
) -> list[tuple[str, int]]:
    """Per-signal-class Contract counts. The Forecast Ledger's reliability
    view will build on top of this once realized returns are joined in."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT signal_class_id, COUNT(*) AS n
            FROM contracts
            GROUP BY signal_class_id
            ORDER BY n DESC
            """
        )
        return [(r[0], int(r[1])) for r in cur.fetchall()]


def contracts_ready_to_score(
    conn: psycopg.Connection[Any],
    as_of_time: datetime,
    horizon_days: int,
) -> list[str]:
    """Return contract_ids whose decision_time + horizon_days <= as_of_time.
    These are eligible for realized-return scoring against equity_prices."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT contract_id FROM contracts
            WHERE decision_time + (%s::int * INTERVAL '1 day') <= %s
            ORDER BY decision_time
            """,
            (horizon_days, as_of_time),
        )
        return [str(r[0]) for r in cur.fetchall()]
