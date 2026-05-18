"""adversarial_agents.py — three test agents for evaluator validation.

Each agent produces a `ForecastOverBuckets` — a probability distribution over
realized-return buckets in the toy world. The agents are deliberately broken or
deliberately sensible test fixtures. They give the evaluator (Brier, log_score,
Forecast Ledger reliability) something to rank.

The three personas (PYRAMID.md Stone 16):

  - ConfidentAgent — always reports a fixed forecast, ignoring emissions. When
    the chosen bucket is NOT the realized one, this is the "confidently-wrong"
    adversarial. Should score near-max Brier and near-Cromwell log_score.

  - UniformAgent — always reports uniform forecast across all buckets, ignoring
    emissions. The "no discrimination" adversarial. Belief never moves regardless
    of evidence. Tests whether the scoreboard sees that a no-discrimination
    agent is useless even though its forecast is a valid probability distribution.

  - BayesianAgent — updates its forecast via Bayes on each emission, using the
    pre-computed bucket-conditional likelihoods from synthetic_market. The
    well-calibrated baseline. Should win every column it is qualified to win
    across many episodes.

Constitution v5 (Phase 1 NEW Cluster A): the agent's hypothesis space is
realized-return BUCKETS (`ReturnBucket`), not hidden states. The toy's hidden
state structure is INVISIBLE to the agent — it lives inside the simulation as
scaffolding only. Agents read emissions and forecast over buckets.

Run: `uv run python -m fingym.toys.adversarial_agents`
"""

import random
from dataclasses import dataclass
from typing import Protocol

from fingym.evaluator.scoring import brier, log_score
from fingym.toys.synthetic_market import (
    RETURN_BUCKETS,
    STATES,
    CompanyState,
    Emission,
    ForecastOverBuckets,
    ReturnBucket,
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
    uniform_forecast_over_buckets,
    update_forecast_over_buckets,
)

# Standard prior used by the BayesianAgent. Uniform — the agent has no prior
# information about the company, so it starts flat across buckets.
DEFAULT_BAYESIAN_PRIOR: ForecastOverBuckets = uniform_forecast_over_buckets()


class Agent(Protocol):
    """The minimal protocol every adversarial / believer agent satisfies.

    `name` is a human-readable label used by the scoreboard.
    `forecast` is the agent's current forecast distribution over realized-return
    buckets — readable any time.
    `observe(emission)` lets the agent (optionally) update on a new emission.
    """

    name: str
    signal_class_id: str

    @property
    def forecast(self) -> ForecastOverBuckets: ...

    def observe(self, emission: Emission) -> None: ...


class ConfidentAgent:
    """Always reports a fixed forecast, ignoring emissions.

    `bucket` is the bucket the agent is confident about; `confidence` is the
    probability mass placed on that bucket. The remaining mass is split equally
    across the other buckets. With `confidence` close to 1.0 and `bucket` NOT
    the realized one, this is the "confidently-wrong" adversarial.
    """

    def __init__(self, bucket: ReturnBucket, confidence: float = 0.95) -> None:
        if not 0.0 < confidence < 1.0:
            raise ValueError(f"confidence must be strictly between 0 and 1, got {confidence}")
        other_p = (1.0 - confidence) / (len(RETURN_BUCKETS) - 1)
        self._forecast: ForecastOverBuckets = {
            b: confidence if b == bucket else other_p for b in RETURN_BUCKETS
        }
        self.name = f"ConfidentAgent({bucket}, p={confidence:.2f})"
        self.signal_class_id = "confident_static"

    @property
    def forecast(self) -> ForecastOverBuckets:
        return dict(self._forecast)

    def observe(self, emission: Emission) -> None:
        # Ignores emissions by design.
        _ = emission


class UniformAgent:
    """Always reports uniform forecast, ignoring emissions.

    The "no discrimination" adversarial. Catches the case where an agent has no
    discriminative power despite being technically a calibrated probability
    distribution.
    """

    def __init__(self) -> None:
        self._forecast: ForecastOverBuckets = uniform_forecast_over_buckets()
        self.name = "UniformAgent"
        self.signal_class_id = "uniform_static"

    @property
    def forecast(self) -> ForecastOverBuckets:
        return dict(self._forecast)

    def observe(self, emission: Emission) -> None:
        # Ignores emissions by design.
        _ = emission


class BayesianAgent:
    """Updates forecast via Bayes over realized-return buckets on each emission.

    Uses the pre-computed bucket-conditional emission likelihoods from
    synthetic_market.BUCKET_CONDITIONAL_LIKELIHOODS. The agent's prior is over
    buckets (not states). Starts uniform unless a custom prior is supplied.

    Cromwell-respecting — the prior must place strictly positive mass on every
    bucket so the Bayes update never multiplies by zero.
    """

    def __init__(
        self, prior: ForecastOverBuckets | None = None, name: str = "BayesianAgent"
    ) -> None:
        if prior is None:
            prior = uniform_forecast_over_buckets()
        prior_sum = sum(prior.values())
        if not 0.999 < prior_sum < 1.001:
            raise ValueError(f"prior must sum to 1 (got {prior_sum})")
        if any(p <= 0.0 for p in prior.values()):
            raise ValueError("prior must assign strictly positive mass to every bucket (Cromwell)")
        self._forecast: ForecastOverBuckets = dict(prior)
        self.name = name
        self.signal_class_id = "bayesian_3state_toy"

    @property
    def forecast(self) -> ForecastOverBuckets:
        return dict(self._forecast)

    def observe(self, emission: Emission) -> None:
        self._forecast = update_forecast_over_buckets(self._forecast, emission)


def print_agent_introductions() -> None:
    """Show each agent's initial forecast and its response to one emission.

    The broken agents (ConfidentAgent, UniformAgent) should produce identical
    forecast rows before and after the emission — they ignore it. The
    BayesianAgent should shift toward higher-return buckets on a `strong` emission.
    """
    confidently_wrong = ConfidentAgent("below_minus_5", confidence=0.95)
    uniform = UniformAgent()
    bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")

    agents: list[Agent] = [confidently_wrong, uniform, bayesian]

    header_buckets = " | ".join(f"{b:>17}" for b in RETURN_BUCKETS)
    header = f"{'agent':<42} | {header_buckets}"

    print("\nAgent introductions — initial forecasts (before any emission)")
    print(header)
    print("-" * len(header))
    for agent in agents:
        f = agent.forecast
        cells = " | ".join(f"{f[b]:>17.3f}" for b in RETURN_BUCKETS)
        print(f"{agent.name:<42} | {cells}")

    emission: Emission = "strong"
    print(f"\nAfter one '{emission}' emission")
    print(header)
    print("-" * len(header))
    for agent in agents:
        agent.observe(emission)
        f = agent.forecast
        cells = " | ".join(f"{f[b]:>17.3f}" for b in RETURN_BUCKETS)
        print(f"{agent.name:<42} | {cells}")


def print_single_episode_demo(
    truth_state: CompanyState = "strengthening",
    n_emissions: int = 12,
    seed: int = 42,
) -> None:
    """Run the three adversarial agents through one episode.

    Truth state defaults to `strengthening`, which will tend to produce realized
    returns in the higher buckets. ConfidentAgent (confident on below_minus_5)
    will end the episode confidently wrong; BayesianAgent should shift its
    forecast toward higher buckets.

    Outputs:
      - End-of-episode realized log return and bucket
      - Per-agent final forecast on the realized bucket
      - Brier and log_score for each agent against the realized bucket
    """
    rng = random.Random(seed)

    confident = ConfidentAgent("below_minus_5", confidence=0.95)
    uniform = UniformAgent()
    bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")

    agents: list[Agent] = [confident, uniform, bayesian]

    print(f"\nSingle episode — truth_state={truth_state}, n_emissions={n_emissions}, seed={seed}")

    for _ in range(n_emissions):
        e = sample_emission(truth_state, rng)
        for a in agents:
            a.observe(e)

    realized_return = realize_return_at_horizon(truth_state, rng)
    realized_bucket = return_to_bucket(realized_return)
    print(f"Realized return at horizon: {realized_return:+.4f} log → bucket = {realized_bucket}")

    print(f"\nEnd-of-episode scoreboard (truth bucket = {realized_bucket})")
    sb_header = f"{'agent':<42} | {'P(realized)':>11} | {'Brier':>7} | {'log_score':>9}"
    print(sb_header)
    print("-" * len(sb_header))
    for a in agents:
        f = a.forecast
        br = brier(f, realized_bucket)
        ls = log_score(f, realized_bucket)
        print(f"{a.name:<42} | {f[realized_bucket]:>11.3f} | {br:>7.3f} | {ls:>9.3f}")


@dataclass(frozen=True)
class AgentMeans:
    """Per-agent aggregate scores across N episodes.

    Returned (as a dict keyed by agent name) by `aggregate_n_episodes`. Used by
    both `run_multi_episode_demo` (printed display) and the integration tests.
    """

    name: str
    mean_brier: float
    mean_log_score: float
    n_episodes: int


def aggregate_n_episodes(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> tuple[dict[ReturnBucket, int], dict[str, AgentMeans]]:
    """Run N episodes; return (realized_bucket_counts, per_agent_means).

    Each episode:
      1. Picks a random hidden state (uniformly) — invisible to agents.
      2. Generates `n_emissions_per_episode` emissions from that state.
      3. Realizes a log return at horizon (drawn from the state-conditional
         distribution) and maps it to a bucket.
      4. Each agent's final forecast is scored against the realized bucket via
         Brier and log_score.

    Deterministic — same arguments produce the same results. The integration
    tests in tests/integration/test_evaluator_ranks_adversaries.py consume this
    function directly so the numbers in the demo and the asserts always agree.
    """
    state_rng = random.Random(base_seed)
    state_choices: list[CompanyState] = list(STATES)
    bucket_counts: dict[ReturnBucket, int] = dict.fromkeys(RETURN_BUCKETS, 0)

    agent_names = [
        "ConfidentAgent(below_minus_5, p=0.95)",
        "UniformAgent",
        "BayesianAgent",
    ]
    raw_scores: dict[str, dict[str, list[float]]] = {
        name: {"brier": [], "log_score": []} for name in agent_names
    }

    for episode_idx in range(n_episodes):
        truth_state = state_rng.choice(state_choices)
        episode_seed = base_seed + episode_idx + 1
        episode_rng = random.Random(episode_seed)

        confident = ConfidentAgent("below_minus_5", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
        all_actors: list[Agent] = [confident, uniform, bayesian]

        for _ in range(n_emissions_per_episode):
            e = sample_emission(truth_state, episode_rng)
            for a in all_actors:
                a.observe(e)

        realized_return = realize_return_at_horizon(truth_state, episode_rng)
        realized_bucket = return_to_bucket(realized_return)
        bucket_counts[realized_bucket] += 1

        for a in all_actors:
            f = a.forecast
            raw_scores[a.name]["brier"].append(brier(f, realized_bucket))
            raw_scores[a.name]["log_score"].append(log_score(f, realized_bucket))

    per_agent: dict[str, AgentMeans] = {
        name: AgentMeans(
            name=name,
            mean_brier=sum(raw_scores[name]["brier"]) / n_episodes,
            mean_log_score=sum(raw_scores[name]["log_score"]) / n_episodes,
            n_episodes=n_episodes,
        )
        for name in agent_names
    }

    return bucket_counts, per_agent


def run_multi_episode_demo(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> None:
    """Print the per-agent summary from `aggregate_n_episodes`.

    Expected ranking on Brier and log_score:
      BayesianAgent (best) < UniformAgent (middle) < ConfidentAgent (worst)

    ConfidentAgent does fine on the few episodes where the realized bucket happens
    to be `below_minus_5`; on the other ~majority of episodes it scores
    catastrophically. UniformAgent's Brier is constant by symmetry (1 - 1/N for
    N buckets). BayesianAgent's forecast moves with the emissions stream, so its
    mean should be visibly lowest.
    """
    bucket_counts, per_agent = aggregate_n_episodes(
        n_episodes=n_episodes,
        n_emissions_per_episode=n_emissions_per_episode,
        base_seed=base_seed,
    )

    print(
        f"\nMulti-episode summary — {n_episodes} episodes, "
        f"{n_emissions_per_episode} emissions each, base_seed = {base_seed}"
    )
    bucket_dist = ", ".join(f"{b}: {c}" for b, c in bucket_counts.items())
    print(f"Realized bucket distribution: {bucket_dist}")

    header = f"{'agent':<42} | {'mean Brier':>10} | {'mean log_sc':>11}"
    print(header)
    print("-" * len(header))

    for means in per_agent.values():
        print(f"{means.name:<42} | {means.mean_brier:>10.3f} | {means.mean_log_score:>11.3f}")


if __name__ == "__main__":
    print_agent_introductions()
    print_single_episode_demo(truth_state="strengthening", seed=42)
    print_single_episode_demo(truth_state="decaying", seed=42)
    run_multi_episode_demo()
