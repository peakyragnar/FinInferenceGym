"""Scoreboard persistence (JSONL).

Append-only line-delimited JSON. One ScoreboardRow per line; the file
grows as test runs / future production runs append rows. The dashboard
(`src/fingym/operator/`) reads from these files to surface the system's
state across sessions.

Format mirrors what Postgres trajectory-store rows will hold in Phase 2
NEW, so migration is a write-target swap, not a schema change.

Two functions:
  - `append_row(row, path)` — append one ScoreboardRow as JSON.
  - `load_scoreboard(path)` — reconstruct a Scoreboard from the file.

The TradeAction / NoAction discriminated union round-trips via pydantic
model_dump / model_validate using the `action_type` field.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fingym.agents.contract import NoAction, TradeAction
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.toys.synthetic_market import ReturnBucket


def append_row(row: ScoreboardRow, path: Path) -> None:
    """Append one ScoreboardRow to `path` as a JSON line.

    Creates the parent directory if missing. The file is opened in append
    mode; concurrent writes from a single process are safe (single-line
    writes), but cross-process locking is not handled — for the toy MVP,
    a single test process writes at a time.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(_row_to_dict(row), default=_default_encode) + "\n")


def load_scoreboard(path: Path) -> Scoreboard:
    """Reconstruct a Scoreboard from a JSONL file.

    Returns an empty Scoreboard if the file does not exist (the dashboard
    can then print 'no data yet' rather than crash). Invalid lines RAISE
    — corrupt scoreboard data is a deploy-time failure, not a silent skip.
    """
    sb = Scoreboard()
    if not path.exists():
        return sb
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        sb.append(_dict_to_row(data))
    return sb


def _row_to_dict(row: ScoreboardRow) -> dict[str, Any]:
    return {
        "agent_id": row.agent_id,
        "signal_class_id": row.signal_class_id,
        "horizon": row.horizon,
        "decision_time": row.decision_time.isoformat(),
        "forecast_distribution": dict(row.forecast_distribution),
        "calibrated_forecast": dict(row.calibrated_forecast),
        "calibrated_expected_return": row.calibrated_expected_return,
        "calibrated_expected_utility": row.calibrated_expected_utility,
        "tradable_edge_score": row.tradable_edge_score,
        "kelly_fraction_applied": row.kelly_fraction_applied,
        "final_action": row.final_action.model_dump(),
        "realized_return": row.realized_return,
        "realized_bucket": row.realized_bucket,
        "brier": row.brier,
        "log_score": row.log_score,
        "realized_edge": row.realized_edge,
    }


def _dict_to_row(data: dict[str, Any]) -> ScoreboardRow:
    action_data = data["final_action"]
    action: TradeAction | NoAction
    if action_data["action_type"] == "trade":
        action = TradeAction.model_validate(action_data)
    else:
        action = NoAction.model_validate(action_data)

    forecast: dict[ReturnBucket, float] = dict(data["forecast_distribution"].items())
    calibrated: dict[ReturnBucket, float] = dict(data["calibrated_forecast"].items())

    return ScoreboardRow(
        agent_id=data["agent_id"],
        signal_class_id=data["signal_class_id"],
        horizon=data["horizon"],
        decision_time=datetime.fromisoformat(data["decision_time"]),
        forecast_distribution=forecast,
        calibrated_forecast=calibrated,
        calibrated_expected_return=data["calibrated_expected_return"],
        calibrated_expected_utility=data["calibrated_expected_utility"],
        tradable_edge_score=data["tradable_edge_score"],
        kelly_fraction_applied=data["kelly_fraction_applied"],
        final_action=action,
        realized_return=data["realized_return"],
        realized_bucket=data["realized_bucket"],
        brier=data["brier"],
        log_score=data["log_score"],
        realized_edge=data["realized_edge"],
    )


def _default_encode(obj: Any) -> Any:
    """Fallback encoder for non-standard JSON types. Pydantic models go
    through model_dump in _row_to_dict already; this is a safety net."""
    if hasattr(obj, "model_dump"):
        result = obj.model_dump()
        return result if isinstance(result, dict) else dict(result)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Cannot encode object of type {type(obj).__name__}: {obj!r}")


__all__ = ["append_row", "load_scoreboard"]
