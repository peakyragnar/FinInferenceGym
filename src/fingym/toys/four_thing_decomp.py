"""four_thing_decomp.py — runnable visualization of Stone 7a.

The four-thing decomposition (S_true, P_AI(S), P_market(S), Action(A)) shown
on three scenarios that produce visibly different scoreboard signatures:

  A. Calibrated agent + monetizable disagreement with market  → edge
  B. Calibrated agent + same belief as market                 → no edge, NoAction correct
  C. Confidently-wrong agent + big gap                        → catastrophic when sized

Layer 1 (Stones 1-7) scored P_AI alone. Layer 2 introduces P_market and the
gap between them. This toy shows why "well-calibrated" does not equal
"has edge" — the gap is the load-bearing thing.

Run: uv run python -m fingym.toys.four_thing_decomp
"""

import math
from typing import Literal

from fingym.evaluator.scoring import brier, log_score

type CompanyState = Literal["strengthening", "stable", "decaying"]
type Belief = dict[CompanyState, float]


# --- The four-thing decomposition, computed -------------------------------------


def gap_on_truth(p_ai: Belief, p_market: Belief, s_true: CompanyState) -> float:
    """P_AI(S_true) - P_market(S_true).

    Positive: agent is more confident on the eventual truth than market.
    Zero:     agent agrees with market — no edge regardless of outcome.
    Negative: agent is LESS confident on the truth than market.
    """
    return p_ai[s_true] - p_market[s_true]


def biggest_gap(p_ai: Belief, p_market: Belief) -> tuple[CompanyState, float]:
    """Find the state with the largest probability gap (signed)."""
    gaps = {state: p_ai[state] - p_market[state] for state in p_ai}
    return max(gaps.items(), key=lambda kv: abs(kv[1]))


def suggested_action(p_ai: Belief, p_market: Belief, gap_threshold: float = 0.10) -> str:
    """Recommend Action(A) given P_AI vs P_market.

    Picks the state with the biggest signed gap. If |gap| < threshold,
    returns NoAction (gap below cost-threshold; not monetizable).
    """
    bet_state, gap = biggest_gap(p_ai, p_market)
    if abs(gap) < gap_threshold:
        return f"NoAction (|gap|={abs(gap):.2f} < threshold {gap_threshold})"
    direction = "long" if gap > 0 else "short"
    return f"TradeAction: {direction} {bet_state} (gap {gap:+.2f})"


def toy_pnl(
    p_ai: Belief, p_market: Belief, s_true: CompanyState, gap_threshold: float = 0.10
) -> float:
    """Stylized P&L proxy. Unit-size bet on the biggest-gap state.

    Wins 1.0 * |gap| if the agent's bet state matches s_true.
    Loses 1.0 * |gap| if it doesn't.
    Returns 0.0 if action is NoAction.

    This is illustrative only; real P&L involves payoff structures, fractional
    Kelly sizing, market impact, and time costs (Stones 13, 14, 33).
    """
    bet_state, gap = biggest_gap(p_ai, p_market)
    if abs(gap) < gap_threshold:
        return 0.0
    sign = 1.0 if gap > 0 else -1.0
    won = bet_state == s_true
    return sign * abs(gap) * (1.0 if won else -1.0)


# --- Pretty-print one scenario --------------------------------------------------


def run_scenario(
    name: str,
    p_ai: Belief,
    p_market: Belief,
    s_true: CompanyState,
) -> dict[str, float | str]:
    """Print the four-thing decomposition for one scenario; return its row."""
    layer1_brier = brier(p_ai, s_true)
    layer1_log = log_score(p_ai, s_true)
    gap_truth = gap_on_truth(p_ai, p_market, s_true)
    action = suggested_action(p_ai, p_market)
    pnl = toy_pnl(p_ai, p_market, s_true)

    print(f"\n=== Scenario {name} ===")
    print(f"  S_true            = {s_true!r}")
    print(f"  P_AI(S)           = {fmt_belief(p_ai)}")
    print(f"  P_market(S)       = {fmt_belief(p_market)}")
    print("  Layer-1 metrics (P_AI vs S_true only — what we taught in Stones 1-7):")
    print(f"    Brier           = {layer1_brier:.4f}")
    print(f"    log_score       = {format_log_score(layer1_log)}")
    print("  Layer-2 metrics (the four-thing decomposition — new at Stone 7a):")
    print(f"    gap on truth    = {gap_truth:+.4f}  (P_AI(S_true) - P_market(S_true))")
    print(f"    Action(A)       = {action}")
    print(f"    toy P&L         = {pnl:+.4f}")

    return {
        "scenario": name,
        "brier": layer1_brier,
        "log_score": format_log_score(layer1_log),
        "gap_on_truth": f"{gap_truth:+.4f}",
        "pnl": f"{pnl:+.4f}",
    }


def fmt_belief(b: Belief) -> str:
    return "{" + ", ".join(f"{k}: {v:.2f}" for k, v in b.items()) + "}"


def format_log_score(x: float) -> str:
    return "+inf" if math.isinf(x) else f"{x:.4f}"


# --- Three scenarios that produce visibly different scoreboard signatures ------


def main() -> None:
    rows: list[dict[str, float | str]] = []

    rows.append(
        run_scenario(
            "A — calibrated + monetizable disagreement",
            p_ai={"strengthening": 0.55, "stable": 0.30, "decaying": 0.15},
            p_market={"strengthening": 0.30, "stable": 0.45, "decaying": 0.25},
            s_true="strengthening",
        )
    )

    rows.append(
        run_scenario(
            "B — calibrated + same belief as market (NoAction correct)",
            p_ai={"strengthening": 0.30, "stable": 0.45, "decaying": 0.25},
            p_market={"strengthening": 0.30, "stable": 0.45, "decaying": 0.25},
            s_true="strengthening",
        )
    )

    rows.append(
        run_scenario(
            "C — confidently wrong + big gap (catastrophic)",
            p_ai={"strengthening": 0.05, "stable": 0.15, "decaying": 0.80},
            p_market={"strengthening": 0.30, "stable": 0.45, "decaying": 0.25},
            s_true="strengthening",
        )
    )

    print("\n=== Side-by-side summary ===")
    header = f"{'Scenario':<55} {'Brier':>8} {'log_score':>10} {'gap':>8} {'P&L':>8}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['scenario']:<55} "
            f"{row['brier']:>8.4f} "
            f"{row['log_score']:>10} "
            f"{row['gap_on_truth']:>8} "
            f"{row['pnl']:>8}"
        )

    print("\nInterpretation:")
    print("  A: calibrated AND big gap on the winning side. Brier modest (~0.32),")
    print("     gap +0.25, P&L positive. Edge made real.")
    print("  B: calibrated but no gap. Brier mediocre (~0.76) — the belief was wishy-")
    print("     washy. But gap=0, NoAction taken, P&L=0. Correctly idle (BIAS_PATTERNS #12).")
    print("  C: confidently wrong on the truth. Brier ~1.57 (near-max),")
    print("     log_score ~3.0 (deep near-Cromwell), gap -0.25 on the truth,")
    print("     P&L negative. Multiple scoreboard columns light up red.")
    print("\nThe four-thing decomposition distinguishes these three agents.")
    print("Layer 1 alone (Brier on P_AI) would not.")


if __name__ == "__main__":
    main()
