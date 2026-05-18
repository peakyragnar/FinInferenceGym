"""synthetic_market.py — the 3-state synthetic-market toy world.

A hidden company occupies one of three states: strengthening, stable, or decaying.
Each tick, the company emits one of three observation kinds: strong, mixed, or weak.
The mapping from state to emission is probabilistic — the likelihood table is the
rule connecting hidden state to visible emissions.

This module is the Layer-3 fixture for evaluator validation. The world is
deliberately constructed so that we know the hidden state and the true likelihoods;
that is what makes it the place where the evaluator's correctness can be checked
against ground truth (PYRAMID.md Stone 15, intuitions.md #7).

The state alphabet (CompanyState) and emission alphabet (Emission) are encoded as
Literal types so mypy enforces the closed hypothesis space at the type level.

Run: `uv run python -m fingym.toys.synthetic_market`

This file implements the surviving Phase 0 parts of Stone 15 after the Constitution
v5 cleanup pass (2026-05-18): the world (likelihood table + emission sampler +
frequency verification) and a single Bayesian believer over the three states. The
pre-v5 two-believer setup, the `STONE_11A_*` prior constants, and the Stone 11a
scoreboard demo were removed by Constitution v5 (see DECISIONS.md "Constitution
tightening v5"). The v5 single-believer-over-realized-returns refactor and the
Forecast Ledger MVP land as Phase 1 NEW Cluster A.
"""

import random
from typing import Literal

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


if __name__ == "__main__":
    print_world_verification(n_per_state=1000, seed=42)
    run(hidden="strengthening", n_emissions=12, seed=42)
    run(hidden="decaying", n_emissions=12, seed=42)
