"""synthetic_market.py — the 3-state synthetic-market toy world.

A hidden company occupies one of three states: strengthening, stable, or decaying.
Each tick, the company emits one of three observation kinds: strong, mixed, or weak.
The mapping from state to emission is probabilistic — the likelihood table is the
rule connecting hidden state to visible emissions.

This module is the Layer-3 fixture for evaluator validation. The world is
deliberately constructed so that we know `S_true` and we know the true likelihoods;
that is what makes it the place where the evaluator's correctness can be checked
against ground truth (PYRAMID.md Stone 15, intuitions.md #7).

The state alphabet (CompanyState) and emission alphabet (Emission) are encoded as
Literal types so mypy enforces the closed hypothesis space at the type level.

Run: `uv run python -m fingym.toys.synthetic_market`

This file implements all four steps of the Stone 15 build: the world
(Step 1), a single Bayesian believer (Step 2), the two-believer scenario
with belief-delta on truth (Step 3), and the scoreboard reproduction of
PYRAMID Stone 11a's worked example (Step 4) — Brier, log_score, and
belief_delta_on_truth as columns on five fixed scenarios.
"""

import random
from typing import Literal

from fingym.evaluator.scoring import belief_delta_on_truth, brier, log_score

type CompanyState = Literal["strengthening", "stable", "decaying"]
type Emission = Literal["strong", "mixed", "weak"]
type LikelihoodTable = dict[CompanyState, dict[Emission, float]]
type Belief = dict[CompanyState, float]

# P(emission | state). Rows sum to 1. This table IS the world.
LIKELIHOODS: LikelihoodTable = {
    "strengthening": {"strong": 0.70, "mixed": 0.20, "weak": 0.10},
    "stable": {"strong": 0.30, "mixed": 0.40, "weak": 0.30},
    "decaying": {"strong": 0.10, "mixed": 0.20, "weak": 0.70},
}

STATES: tuple[CompanyState, ...] = ("strengthening", "stable", "decaying")
EMISSIONS: tuple[Emission, ...] = ("strong", "mixed", "weak")

# Priors from PYRAMID.md Stone 11a's worked example. Agent leans toward
# strengthening; market leans toward decaying. Both use the same LIKELIHOODS
# table — matched-likelihood, different-prior setup.
STONE_11A_AGENT_PRIOR: Belief = {
    "strengthening": 0.55,
    "stable": 0.30,
    "decaying": 0.15,
}
STONE_11A_MARKET_PRIOR: Belief = {
    "strengthening": 0.30,
    "stable": 0.30,
    "decaying": 0.40,
}


def sample_emission(state: CompanyState, rng: random.Random) -> Emission:
    """Emit one observation from the given company state.

    Uses the cumulative distribution of LIKELIHOODS[state] to sample.
    """
    u = rng.random()
    cumulative = 0.0
    for emission in EMISSIONS:
        cumulative += LIKELIHOODS[state][emission]
        if u < cumulative:
            return emission
    # Floating-point safety net — unreachable if rows sum to 1.
    return EMISSIONS[-1]


def empirical_frequencies(state: CompanyState, n: int, rng: random.Random) -> dict[Emission, float]:
    """Sample n emissions from `state` and return the empirical frequency table."""
    counts: dict[Emission, int] = dict.fromkeys(EMISSIONS, 0)
    for _ in range(n):
        counts[sample_emission(state, rng)] += 1
    return {e: counts[e] / n for e in EMISSIONS}


def print_world_verification(n_per_state: int = 1000, seed: int = 42) -> None:
    """Sample n emissions from each state and print empirical vs expected."""
    rng = random.Random(seed)
    print(f"\nWorld verification — {n_per_state} samples per state, seed = {seed}")
    header = f"{'state':<14} | {'strong':>22} | {'mixed':>22} | {'weak':>22}"
    print(header)
    print("-" * len(header))
    for state in STATES:
        expected = LIKELIHOODS[state]
        empirical = empirical_frequencies(state, n_per_state, rng)
        cells = [f"{empirical[e]:.3f} (expected {expected[e]:.2f})" for e in EMISSIONS]
        print(f"{state:<14} | {cells[0]:>22} | {cells[1]:>22} | {cells[2]:>22}")
    print()


def likelihood(emission: Emission, state: CompanyState) -> float:
    """P(emission | state) — one entry of the likelihood table."""
    return LIKELIHOODS[state][emission]


def update(belief: Belief, emission: Emission) -> Belief:
    """One Bayesian update: posterior = prior * likelihood / normalize."""
    unnorm: Belief = {state: belief[state] * likelihood(emission, state) for state in belief}
    total = sum(unnorm.values())
    return {state: p / total for state, p in unnorm.items()}


def run(hidden: CompanyState, n_emissions: int, seed: int) -> None:
    """Run a single inference episode and print belief evolution."""
    rng = random.Random(seed)
    belief: Belief = dict.fromkeys(STATES, 1.0 / len(STATES))

    print(f"\nhidden state = {hidden}   n_emissions = {n_emissions}   seed = {seed}")
    header = f"{'tick':>4} | {'emission':<10} | {'P(strg)':>8} | {'P(stbl)':>8} | {'P(dec)':>8}"
    print(header)
    print("-" * len(header))
    print(
        f"{0:>4} | {'(prior)':<10} | "
        f"{belief['strengthening']:>8.3f} | "
        f"{belief['stable']:>8.3f} | "
        f"{belief['decaying']:>8.3f}"
    )
    for i in range(1, n_emissions + 1):
        e = sample_emission(hidden, rng)
        belief = update(belief, e)
        print(
            f"{i:>4} | {e:<10} | "
            f"{belief['strengthening']:>8.3f} | "
            f"{belief['stable']:>8.3f} | "
            f"{belief['decaying']:>8.3f}"
        )


def run_two_believers(
    hidden: CompanyState,
    n_emissions: int,
    seed: int,
    agent_prior: Belief,
    market_prior: Belief,
) -> None:
    """Run a two-believer episode and print belief evolution side by side.

    Both believers see the same emission stream and update via the same
    Bayesian rule (matched likelihoods — both use LIKELIHOODS). What differs
    is their starting prior.

    The `gap on truth` column is `P_AI(S_true) - P_market(S_true)` — the
    Stone 11a measurement of belief disagreement on the actually-correct state.
    Positive = agent has edge. Zero = no edge. Negative = anti-edge.
    """
    rng = random.Random(seed)
    p_ai: Belief = dict(agent_prior)
    p_market: Belief = dict(market_prior)

    print(f"\nhidden = {hidden}   n_emissions = {n_emissions}   seed = {seed}")
    header = (
        f"{'tick':>4} | {'emission':<8} | "
        f"{'P_AI(strg)':>10} | {'P_AI(stbl)':>10} | {'P_AI(dec)':>10} | "
        f"{'P_mkt(strg)':>11} | {'P_mkt(stbl)':>11} | {'P_mkt(dec)':>11} | "
        f"{'gap on truth':>12}"
    )
    print(header)
    print("-" * len(header))

    def print_row(tick_label: str, emission_label: str, ai: Belief, mkt: Belief) -> None:
        gap = ai[hidden] - mkt[hidden]
        print(
            f"{tick_label:>4} | {emission_label:<8} | "
            f"{ai['strengthening']:>10.3f} | "
            f"{ai['stable']:>10.3f} | "
            f"{ai['decaying']:>10.3f} | "
            f"{mkt['strengthening']:>11.3f} | "
            f"{mkt['stable']:>11.3f} | "
            f"{mkt['decaying']:>11.3f} | "
            f"{gap:>+12.3f}"
        )

    print_row("0", "(prior)", p_ai, p_market)

    for i in range(1, n_emissions + 1):
        e = sample_emission(hidden, rng)
        p_ai = update(p_ai, e)
        p_market = update(p_market, e)
        print_row(str(i), e, p_ai, p_market)


def run_scoreboard_demo() -> None:
    """Reproduce PYRAMID Stone 11a's worked example as a scoreboard table.

    Five fixed scenarios with explicit (P_AI, P_market, S_true) triples,
    each evaluated by three columns: Brier, log_score, belief_delta_on_truth.

    The point:
      - A/B/C share the same P_AI and S_true. Brier and log_score are
        IDENTICAL across them — Layer-1 metrics see only P_AI vs truth.
      - The `gap on truth` column varies +0.25 / 0.00 / -0.25 across A/B/C
        because only it takes P_market into account.
      - D and E both have the agent confidently wrong on truth (catastrophic
        Brier and log_score) — but D has anti-edge (market less wrong) and
        E has no informational gap to lose (market equally wrong).
    """
    s_true: CompanyState = "strengthening"

    agent_calibrated: Belief = {
        "strengthening": 0.55,
        "stable": 0.30,
        "decaying": 0.15,
    }
    agent_wrong: Belief = {
        "strengthening": 0.05,
        "stable": 0.15,
        "decaying": 0.80,
    }

    market_bearish: Belief = {
        "strengthening": 0.30,
        "stable": 0.30,
        "decaying": 0.40,
    }
    market_neutral: Belief = {
        "strengthening": 0.55,
        "stable": 0.30,
        "decaying": 0.15,
    }
    market_bullish: Belief = {
        "strengthening": 0.80,
        "stable": 0.10,
        "decaying": 0.10,
    }
    market_wrong: Belief = {
        "strengthening": 0.05,
        "stable": 0.15,
        "decaying": 0.80,
    }

    scenarios: list[tuple[str, str, Belief, Belief]] = [
        ("A", "real edge", agent_calibrated, market_bearish),
        ("B", "no edge", agent_calibrated, market_neutral),
        ("C", "anti-edge", agent_calibrated, market_bullish),
        ("D", "catastrophic", agent_wrong, market_bearish),
        ("E", "both wrong, agree", agent_wrong, market_wrong),
    ]

    print(f"\nStone 11a scoreboard — S_true = {s_true}")
    header = (
        f"{'scenario':<22} | "
        f"{'P_AI(strg)':>10} | {'P_mkt(strg)':>11} | "
        f"{'Brier':>7} | {'log_score':>9} | {'gap on truth':>12}"
    )
    print(header)
    print("-" * len(header))

    for label, name, p_ai, p_market in scenarios:
        b = brier(p_ai, s_true)
        ls = log_score(p_ai, s_true)
        d = belief_delta_on_truth(p_ai, p_market, s_true)
        row_label = f"{label}: {name}"
        print(
            f"{row_label:<22} | "
            f"{p_ai[s_true]:>10.3f} | {p_market[s_true]:>11.3f} | "
            f"{b:>7.4f} | {ls:>9.4f} | {d:>+12.3f}"
        )


if __name__ == "__main__":
    print_world_verification(n_per_state=1000, seed=42)
    run(hidden="strengthening", n_emissions=12, seed=42)
    run(hidden="decaying", n_emissions=12, seed=42)
    run_two_believers(
        hidden="strengthening",
        n_emissions=12,
        seed=42,
        agent_prior=STONE_11A_AGENT_PRIOR,
        market_prior=STONE_11A_MARKET_PRIOR,
    )
    run_two_believers(
        hidden="decaying",
        n_emissions=12,
        seed=42,
        agent_prior=STONE_11A_AGENT_PRIOR,
        market_prior=STONE_11A_MARKET_PRIOR,
    )
    run_scoreboard_demo()
