"""synthetic_market.py — the 3-state synthetic-market toy world.

A hidden company occupies one of three states: strengthening, stable, or decaying.
Each tick, the company emits one of three observation kinds: strong, mixed, or weak.
At horizon, the company produces a realized log return drawn from a state-conditional
normal distribution. The state structure is INTERNAL to the simulation — agents
never see it. Agents observe the emission stream and forecast a distribution over
realized-return BUCKETS at horizon.

This module is the Layer-3 fixture for evaluator validation. The world is
deliberately constructed so we know the ground truth (state + the state-conditional
emission + return distributions); that is what makes it the place where the
evaluator's correctness can be checked against ground truth (PYRAMID.md Stone 15,
intuitions.md #7).

Under Constitution v5 (Stones 7b, 11b):
- The agent's hypothesis space is realized-return buckets (NOT states).
- The toy keeps the 3-state hidden generating process as INVISIBLE simulation
  scaffolding — a convenient way to construct a non-trivial joint distribution of
  (emission stream, realized return).
- The bucket-conditional emission likelihood `P(emission | bucket)` is pre-computed
  from the toy's structure and exposed for agents that want to do Bayes over buckets.

The state alphabet (CompanyState), emission alphabet (Emission), and return-bucket
alphabet (ReturnBucket) are all encoded as Literal types so mypy enforces the closed
hypothesis spaces at the type level.

Run: `uv run python -m fingym.toys.synthetic_market`
"""

import random
from statistics import NormalDist
from typing import Literal

type CompanyState = Literal["strengthening", "stable", "decaying"]
type Emission = Literal["strong", "mixed", "weak"]
type ReturnBucket = Literal[
    "below_minus_5",
    "minus_5_to_0",
    "zero_to_plus_5",
    "plus_5_to_plus_10",
    "above_plus_10",
]
type LikelihoodTable = dict[CompanyState, dict[Emission, float]]
type Belief = dict[CompanyState, float]
type ForecastOverBuckets = dict[ReturnBucket, float]

# P(emission | state). Rows sum to 1. This table IS the world.
LIKELIHOODS: LikelihoodTable = {
    "strengthening": {"strong": 0.70, "mixed": 0.20, "weak": 0.10},
    "stable": {"strong": 0.30, "mixed": 0.40, "weak": 0.30},
    "decaying": {"strong": 0.10, "mixed": 0.20, "weak": 0.70},
}

STATES: tuple[CompanyState, ...] = ("strengthening", "stable", "decaying")
EMISSIONS: tuple[Emission, ...] = ("strong", "mixed", "weak")
RETURN_BUCKETS: tuple[ReturnBucket, ...] = (
    "below_minus_5",
    "minus_5_to_0",
    "zero_to_plus_5",
    "plus_5_to_plus_10",
    "above_plus_10",
)

# Realized log return at horizon is drawn from N(mean, std) per state.
# Strengthening pays positive returns; decaying pays negative; stable centers at 0.
STATE_RETURN_PARAMS: dict[CompanyState, tuple[float, float]] = {
    "strengthening": (0.07, 0.04),
    "stable": (0.00, 0.03),
    "decaying": (-0.07, 0.04),
}

# Bucket boundaries in log-return space. Upper edge of each bucket; the last
# bucket extends to +infinity.
_BUCKET_UPPER_EDGES: dict[ReturnBucket, float] = {
    "below_minus_5": -0.05,
    "minus_5_to_0": 0.00,
    "zero_to_plus_5": 0.05,
    "plus_5_to_plus_10": 0.10,
    "above_plus_10": float("inf"),
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
    """One Bayesian update over states: posterior = prior * likelihood / normalize.

    Kept for the simulation's own internal use and legacy demos. Agents under v5
    do NOT use this — they update over realized-return buckets via
    `update_forecast_over_buckets()`.
    """
    unnorm: Belief = {state: belief[state] * likelihood(emission, state) for state in belief}
    total = sum(unnorm.values())
    return {state: p / total for state, p in unnorm.items()}


# ----------------------------------------------------------------------------
# v5 — realized returns + bucket-conditional likelihoods.
# State structure is internal scaffolding only; agents see emissions and forecast
# over realized-return buckets.
# ----------------------------------------------------------------------------


def realize_return_at_horizon(state: CompanyState, rng: random.Random) -> float:
    """Draw a realized log return at horizon for the given hidden state.

    Uses the state-conditional N(mean, std) distribution from STATE_RETURN_PARAMS.
    This is invisible to the agent — only the toy world calls this.
    """
    mean, std = STATE_RETURN_PARAMS[state]
    return rng.gauss(mean, std)


def return_to_bucket(realized_log_return: float) -> ReturnBucket:
    """Map a realized log return to its ReturnBucket label.

    Bucket boundaries are at -5%, 0%, +5%, +10% in log-return space. The lowest
    bucket extends to -infinity; the highest to +infinity.
    """
    for bucket in RETURN_BUCKETS:
        if realized_log_return < _BUCKET_UPPER_EDGES[bucket]:
            return bucket
    return RETURN_BUCKETS[-1]


def _p_bucket_given_state(state: CompanyState, bucket: ReturnBucket) -> float:
    """P(realized return falls in bucket | state). Computed from the state's normal CDF."""
    mean, std = STATE_RETURN_PARAMS[state]
    dist = NormalDist(mu=mean, sigma=std)
    upper = _BUCKET_UPPER_EDGES[bucket]
    # Find the lower edge: it's the upper edge of the preceding bucket, or -inf
    # if this is the lowest bucket.
    idx = RETURN_BUCKETS.index(bucket)
    if idx == 0:
        lower_cdf = 0.0
    else:
        prev_upper = _BUCKET_UPPER_EDGES[RETURN_BUCKETS[idx - 1]]
        lower_cdf = dist.cdf(prev_upper)
    upper_cdf = 1.0 if upper == float("inf") else dist.cdf(upper)
    return upper_cdf - lower_cdf


def _compute_bucket_conditional_emission_likelihoods() -> dict[ReturnBucket, dict[Emission, float]]:
    """Pre-compute P(emission | bucket), marginalizing over the hidden state.

    Derived once at module import from the toy's structure:

        P(emission | bucket) = sum over states of
                                 P(emission | state) * P(state | bucket)
        P(state | bucket)   = P(bucket | state) * P(state) / P(bucket)
        P(state)            = uniform 1/3 (the toy's state prior)

    The returned dict is exposed as `BUCKET_CONDITIONAL_LIKELIHOODS` for agents
    that update beliefs over buckets via Bayes.
    """
    n_states = len(STATES)
    p_state = 1.0 / n_states

    # P(state | bucket) via Bayes from P(bucket | state) and uniform P(state)
    p_bucket = {
        bucket: sum(_p_bucket_given_state(s, bucket) * p_state for s in STATES)
        for bucket in RETURN_BUCKETS
    }
    p_state_given_bucket: dict[ReturnBucket, dict[CompanyState, float]] = {
        bucket: {
            state: _p_bucket_given_state(state, bucket) * p_state / p_bucket[bucket]
            for state in STATES
        }
        for bucket in RETURN_BUCKETS
    }

    # P(emission | bucket) = sum over states of P(emission | state) * P(state | bucket)
    return {
        bucket: {
            emission: sum(
                LIKELIHOODS[state][emission] * p_state_given_bucket[bucket][state]
                for state in STATES
            )
            for emission in EMISSIONS
        }
        for bucket in RETURN_BUCKETS
    }


# Pre-computed once. Agents read this for Bayes over buckets.
BUCKET_CONDITIONAL_LIKELIHOODS: dict[ReturnBucket, dict[Emission, float]] = (
    _compute_bucket_conditional_emission_likelihoods()
)


def bucket_likelihood(emission: Emission, bucket: ReturnBucket) -> float:
    """P(emission | bucket) — the v5 likelihood the agent uses for Bayes over buckets."""
    return BUCKET_CONDITIONAL_LIKELIHOODS[bucket][emission]


def update_forecast_over_buckets(
    forecast: ForecastOverBuckets, emission: Emission
) -> ForecastOverBuckets:
    """One Bayesian update over realized-return buckets.

    posterior(bucket) ∝ prior(bucket) * P(emission | bucket)

    This is the v5-native cognition update for agents in the toy world. The agent
    never reasons over states — only over buckets.
    """
    unnorm: ForecastOverBuckets = {
        bucket: forecast[bucket] * bucket_likelihood(emission, bucket) for bucket in forecast
    }
    total = sum(unnorm.values())
    return {bucket: p / total for bucket, p in unnorm.items()}


def uniform_forecast_over_buckets() -> ForecastOverBuckets:
    """A uniform prior over realized-return buckets. Each bucket gets 1/N probability."""
    return dict.fromkeys(RETURN_BUCKETS, 1.0 / len(RETURN_BUCKETS))


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
