"""Single-command operator report.

Four sections in fixed order:
  1. Scoreboard summary    — per-agent metrics table
  2. Track C attribution    — incremental_AI_edge per non-Baseline agent
  3. Memory state           — L3 promoted + L2 probationary inventory
  4. Recent gate activity   — promotions / demotions / retirements

Each section guards against the "no data" case (prints a brief note
rather than crashing). Output is plain text, suitable for terminal
viewing and for piping into a log file.
"""

from __future__ import annotations

from pathlib import Path

from fingym.agents.contract import NoAction, TradeAction
from fingym.baseline.market_state import BASELINE_AGENT_ID
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.evaluator.scoreboard_io import load_scoreboard
from fingym.memory.schema import MemoryArtifact
from fingym.memory.storage import load_probationary_skills, load_promoted_skills


def print_report(
    scoreboard_path: Path,
    l3_dir: Path,
    l2_dir: Path,
) -> None:
    """Print the full operator report to stdout."""
    sb = load_scoreboard(scoreboard_path)
    l3 = load_promoted_skills(l3_dir)
    l2 = load_probationary_skills(l2_dir)

    print("=" * 72)
    print(" FinInferenceGym — Operator Report")
    print("=" * 72)
    print(f" Scoreboard:  {scoreboard_path}  ({sb.total_rows()} rows)")
    print(f" L3 dir:      {l3_dir}  ({len(l3)} promoted skills)")
    print(f" L2 dir:      {l2_dir}  ({len(l2)} probationary skills)")
    print("=" * 72)
    print()

    _print_scoreboard_section(sb)
    _print_attribution_section(sb)
    _print_memory_section(l3, l2)
    _print_gate_log_section(l3, l2)


# ---------------------------------------------------------------------------
# Section 1: Scoreboard summary
# ---------------------------------------------------------------------------


def _print_scoreboard_section(sb: Scoreboard) -> None:
    print("[1] Scoreboard summary")
    print("-" * 72)
    if sb.total_rows() == 0:
        print("    (no Scoreboard rows; run an integration test that writes to the path)")
        print()
        return

    agent_ids = _unique_agent_ids(sb)
    print(
        f"    {'agent_id':<28}  {'rows':>6}  {'trades':>6}  {'noact':>6}  "
        f"{'mean_brier':>10}  {'mean_edge':>10}"
    )
    for agent_id in agent_ids:
        rows = sb.filter_by_agent(agent_id)
        trades = sum(1 for r in rows if isinstance(r.final_action, TradeAction))
        noactions = sum(1 for r in rows if isinstance(r.final_action, NoAction))
        try:
            mean_brier = sb.mean_brier(rows)
        except ValueError:
            mean_brier = float("nan")
        try:
            mean_edge = sb.mean_realized_edge(rows)
        except ValueError:
            mean_edge = float("nan")
        print(
            f"    {agent_id:<28}  {len(rows):>6}  {trades:>6}  {noactions:>6}  "
            f"{mean_brier:>10.4f}  {mean_edge:>+10.4f}"
        )
    print()


# ---------------------------------------------------------------------------
# Section 2: Track C attribution
# ---------------------------------------------------------------------------


def _print_attribution_section(sb: Scoreboard) -> None:
    print("[2] Track C attribution (incremental_AI_edge vs Market-State Baseline)")
    print("-" * 72)
    if sb.total_rows() == 0:
        print("    (no Scoreboard rows)")
        print()
        return

    baseline_rows = sb.filter_by_agent(BASELINE_AGENT_ID)
    if not baseline_rows:
        print(f"    (no rows under agent_id={BASELINE_AGENT_ID!r}; Track C attribution")
        print("     requires the Market-State Baseline to have logged forecasts)")
        print()
        return

    agent_ids = [aid for aid in _unique_agent_ids(sb) if aid != BASELINE_AGENT_ID]
    if not agent_ids:
        print("    (no non-Baseline agents to attribute)")
        print()
        return

    print(f"    {'agent_id':<28}  {'incremental_AI_edge':>22}")
    for agent_id in agent_ids:
        try:
            delta = sb.incremental_ai_edge(agent_id, BASELINE_AGENT_ID)
            print(f"    {agent_id:<28}  {delta:>+22.4f}")
        except ValueError as e:
            print(f"    {agent_id:<28}  (error: {e})")
    print()


# ---------------------------------------------------------------------------
# Section 3: Memory state
# ---------------------------------------------------------------------------


def _print_memory_section(
    l3: list[MemoryArtifact],
    l2: list[MemoryArtifact],
) -> None:
    print("[3] Memory state")
    print("-" * 72)

    print(f"    L3 promoted ({len(l3)}):")
    if not l3:
        print("        (none yet)")
    else:
        for art in l3:
            horizons = ", ".join(art.domain_of_validity.horizons) or "(none)"
            content_one_line = " ".join(art.content.split())[:80]
            print(f"        - {art.id}")
            print(f"            horizons: {horizons}")
            print(f"            content:  {content_one_line}")
    print()

    print(f"    L2 probationary ({len(l2)}):")
    if not l2:
        print("        (none yet)")
    else:
        for art in l2:
            horizons = ", ".join(art.domain_of_validity.horizons) or "(none)"
            cycles = _count_l2_cycles(art)
            retired = _is_retired(art)
            tag = " [retired]" if retired else f" [cycles: {cycles}]"
            content_one_line = " ".join(art.content.split())[:80]
            print(f"        - {art.id}{tag}")
            print(f"            horizons: {horizons}")
            print(f"            content:  {content_one_line}")
    print()


# ---------------------------------------------------------------------------
# Section 4: Recent gate activity
# ---------------------------------------------------------------------------


def _print_gate_log_section(
    l3: list[MemoryArtifact],
    l2: list[MemoryArtifact],
) -> None:
    print("[4] Recent gate activity")
    print("-" * 72)
    events: list[tuple[str, str, str, str]] = []  # (timestamp, action, artifact_id, reason)
    for art in l3 + l2:
        for entry in art.audit_trail:
            events.append(
                (
                    entry.timestamp.isoformat(),
                    entry.action,
                    art.id,
                    entry.reason,
                )
            )
    if not events:
        print("    (no gate activity yet)")
        print()
        return

    events.sort(reverse=True)  # most recent first
    for ts, action, artifact_id, reason in events[:20]:  # cap at 20 entries
        reason_clean = " ".join(reason.split())[:120]
        print(f"    {ts}  {action:<10}  {artifact_id}")
        print(f"        {reason_clean}")
    if len(events) > 20:
        print(f"    ... ({len(events) - 20} more events not shown)")
    print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_agent_ids(sb: Scoreboard) -> list[str]:
    """First-seen order of distinct agent_ids in the Scoreboard."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for r in sb.rows:
        if r.agent_id in seen_set:
            continue
        seen.append(r.agent_id)
        seen_set.add(r.agent_id)
    return seen


def _count_l2_cycles(artifact: MemoryArtifact) -> int:
    return sum(
        1
        for entry in artifact.audit_trail
        if entry.action == "proposed" and entry.by == "system_revalidation"
    )


def _is_retired(artifact: MemoryArtifact) -> bool:
    for entry in reversed(artifact.audit_trail):
        if entry.action == "retired":
            return True
        if entry.action in ("promoted", "demoted"):
            return False
    return False


# Re-export the unused-import for type-checking happiness; mypy treats
# the ScoreboardRow import as needed since we narrow with isinstance.
__all__ = ["ScoreboardRow", "print_report"]
