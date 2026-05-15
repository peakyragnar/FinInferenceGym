"""market_delta_scoring.py — runnable visualization of Stone 11a.

The load-bearing observation of Layer 2: **same agent belief, same
outcome — but different market contexts produce different edge.**

Layer 1 scoring rules (Brier, log score) see only `P_AI` and `S_true`.
They do not see `P_market`. So three scenarios with the same belief
and same outcome but different markets produce IDENTICAL Brier and
log_score numbers. Edge is invisible to Layer 1.

Stone 11a adds the gap column. It is the first column on the
scoreboard that takes `P_market` into the math. With this column,
the three scenarios produce three different numbers.

Run: uv run python -m fingym.toys.market_delta_scoring
"""

from typing import Literal

from fingym.evaluator.scoring import brier, log_score

type CompanyState = Literal["strengthening", "stable", "decaying"]
type Belief = dict[CompanyState, float]


def gap_on_truth(p_ai: Belief, p_market: Belief, s_true: CompanyState) -> float:
    """`P_AI(S_true) - P_market(S_true)`.

    Positive: agent more confident on the truth than market (edge).
    Zero:     agent agrees with market (no edge to extract).
    Negative: agent less confident on the truth than market (anti-edge).
    """
    return p_ai[s_true] - p_market[s_true]


def fmt_belief(b: Belief) -> str:
    """Compact one-line rendering of a belief distribution."""
    return "{" + ", ".join(f"{k}: {v:.2f}" for k, v in b.items()) + "}"


def run_scenario(
    label: str,
    p_ai: Belief,
    p_market: Belief,
    s_true: CompanyState,
) -> dict[str, str]:
    """Print full breakdown for one scenario; return its summary row."""
    layer1_brier = brier(p_ai, s_true)
    layer1_log = log_score(p_ai, s_true)
    gap = gap_on_truth(p_ai, p_market, s_true)

    print(f"\n--- {label} ---")
    print(f"  S_true        = {s_true}")
    print(f"  P_AI(S)       = {fmt_belief(p_ai)}")
    print(f"  P_market(S)   = {fmt_belief(p_market)}")
    print()
    print("  Layer-1 scoring (sees only P_AI and S_true; ignores P_market):")
    print(f"    Brier       = {layer1_brier:.4f}")
    print(f"    log_score   = {layer1_log:.4f}")
    print()
    print("  Stone 11a scoring (sees P_AI, P_market, and S_true):")
    print(f"    Gap on truth = {gap:+.4f}   (= P_AI({s_true}) - P_market({s_true}))")

    return {
        "label": label,
        "brier": f"{layer1_brier:.4f}",
        "log_score": f"{layer1_log:.4f}",
        "gap": f"{gap:+.4f}",
    }


def main() -> None:
    print("=== Stone 11a — Market-Delta Scoring ===\n")
    print("Five scenarios. Same hypothesis space: {strengthening, stable, decaying}.")
    print("Same outcome (S_true = strengthening) in all five.")
    print("What varies between scenarios: P_AI and/or P_market.\n")

    rows: list[dict[str, str]] = []

    # --- A, B, C: same agent belief, same outcome, varying P_market ---
    same_p_ai: Belief = {
        "strengthening": 0.55,
        "stable": 0.30,
        "decaying": 0.15,
    }

    rows.append(
        run_scenario(
            "A: Calibrated + monetizable disagreement (real edge)",
            p_ai=same_p_ai,
            p_market={
                "strengthening": 0.30,
                "stable": 0.45,
                "decaying": 0.25,
            },
            s_true="strengthening",
        )
    )

    rows.append(
        run_scenario(
            "B: Calibrated + agrees with market (no edge to extract)",
            p_ai=same_p_ai,
            p_market=same_p_ai,  # market belief identical to agent's
            s_true="strengthening",
        )
    )

    rows.append(
        run_scenario(
            "C: Calibrated + market more confident on truth (anti-edge)",
            p_ai=same_p_ai,
            p_market={
                "strengthening": 0.80,
                "stable": 0.15,
                "decaying": 0.05,
            },
            s_true="strengthening",
        )
    )

    # --- D, E: agent confidently wrong; varying P_market ---
    confidently_wrong: Belief = {
        "strengthening": 0.05,
        "stable": 0.15,
        "decaying": 0.80,
    }

    rows.append(
        run_scenario(
            "D: Confidently wrong + big gap (catastrophic — two red flags)",
            p_ai=confidently_wrong,
            p_market={
                "strengthening": 0.30,
                "stable": 0.45,
                "decaying": 0.25,
            },
            s_true="strengthening",
        )
    )

    rows.append(
        run_scenario(
            "E: Both wrong + agree (Layer-1 catastrophic; no edge to lose)",
            p_ai=confidently_wrong,
            p_market=confidently_wrong,  # market equally wrong
            s_true="strengthening",
        )
    )

    # --- Side-by-side summary ---
    print("\n\n=== Side-by-side summary ===\n")
    header = f"{'Scenario':<60} {'Brier':>8} {'log_score':>10} {'Gap':>10}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['label']:<60} {row['brier']:>8} {row['log_score']:>10} {row['gap']:>10}")

    print(
        "\n"
        "Patterns to notice:\n"
        "\n"
        "  A, B, C — same agent belief, same outcome. Brier and log_score\n"
        "             are IDENTICAL across all three (0.3150 / 0.5978).\n"
        "             The Gap column varies (+0.25, 0.00, -0.25) — only\n"
        "             this column shows the difference between real edge,\n"
        "             no edge, and anti-edge. Layer 1 alone is blind to this.\n"
        "\n"
        "  D — agent's belief was catastrophically wrong (5% on the truth).\n"
        "      Brier is near-max (1.57). log_score is deep at 3.00.\n"
        "      AND the Gap is negative (-0.25) — the agent monetized in\n"
        "      the wrong direction with size. Three corroborating red flags.\n"
        "\n"
        "  E — same catastrophic Brier and log_score as D, because the\n"
        "      agent's belief is the same. But the market was equally wrong,\n"
        "      so the Gap is zero. No edge to lose, despite the bad inference.\n"
        "      Same Layer-1 signals; very different Layer-2 interpretation.\n"
        "\n"
        "Aggregating Gap-on-truth across many predictions tells you whether\n"
        "the agent has systematic edge:\n"
        "\n"
        "  Mean Gap > 0    →  agent is systematically more confident on the\n"
        "                     truth than the market — real edge over time.\n"
        "  Mean Gap ≈ 0    →  agent agrees with market on average — no edge.\n"
        "  Mean Gap < 0    →  agent is systematically less confident on the\n"
        "                     truth than market — losing to smarter counter-\n"
        "                     parties. Anti-edge.\n"
    )


if __name__ == "__main__":
    main()
