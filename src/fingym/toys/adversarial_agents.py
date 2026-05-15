"""adversarial_agents.py — three test agents for evaluator validation.

Each agent produces a Belief over the 3-state company space defined in
`synthetic_market.py`. None of them have to be "intelligent" — that is the
point. They are test fixtures whose deliberately-broken (or deliberately-
sensible) behaviour gives the evaluator something to rank.

The three personas (PYRAMID.md Stone 16):

  - ConfidentAgent — always reports a fixed belief, ignoring emissions.
    When the chosen state is NOT the truth, this is the "confidently-wrong"
    adversarial. Should score near-max Brier and near-Cromwell log_score.

  - UniformAgent — always reports uniform belief, ignoring emissions.
    The "always-50%" adversarial. Never moves regardless of evidence.
    Tests whether the scoreboard sees that a no-discrimination agent is
    useless even if its belief is technically a valid probability
    distribution.

  - BayesianAgent — wraps the same Bayes update used by `run_two_believers`
    in synthetic_market.py. The well-calibrated baseline. Should win every
    column it is qualified to win, across many episodes.

The deliberately-broken agents (ConfidentAgent, UniformAgent) ignore
emissions entirely. Their belief on tick 100 is identical to tick 0. That
is the failure mode being tested: an agent that does not update is the
limit case the scoreboard must catch.

Step 1 of Stone 16: this module defines the Agent protocol and the three
concrete classes, plus an introduction demo that prints each agent's
belief before and after one emission. Steps 2-4 (single-episode scoring,
multi-episode aggregation, inflection check) land in subsequent edits.

Run: `uv run python -m fingym.toys.adversarial_agents`
"""

import random
from dataclasses import dataclass
from typing import Protocol

from fingym.evaluator.scoring import belief_delta_on_truth, brier, log_score
from fingym.toys.synthetic_market import (
    STATES,
    STONE_11A_AGENT_PRIOR,
    STONE_11A_MARKET_PRIOR,
    Belief,
    CompanyState,
    Emission,
    sample_emission,
    update,
)


class Agent(Protocol):
    """The minimal protocol every adversarial / believer agent satisfies.

    `name` is a human-readable label used by the scoreboard.
    `belief` is the agent's current belief — readable any time.
    `observe(emission)` lets the agent (optionally) update on a new emission.
    """

    name: str

    @property
    def belief(self) -> Belief: ...

    def observe(self, emission: Emission) -> None: ...


class ConfidentAgent:
    """Always reports a fixed belief, ignoring emissions.

    `state` is the state the agent is confident about; `confidence` is the
    probability mass placed on that state. The remaining mass is split
    equally across the other states. With `confidence` close to 1.0 and
    `state` NOT the truth, this is the "confidently-wrong" adversarial.
    """

    def __init__(self, state: CompanyState, confidence: float = 0.95) -> None:
        if not 0.0 < confidence < 1.0:
            raise ValueError(f"confidence must be strictly between 0 and 1, got {confidence}")
        other_p = (1.0 - confidence) / (len(STATES) - 1)
        self._belief: Belief = {s: confidence if s == state else other_p for s in STATES}
        self.name = f"ConfidentAgent({state}, p={confidence:.2f})"

    @property
    def belief(self) -> Belief:
        return dict(self._belief)

    def observe(self, emission: Emission) -> None:
        # Ignores emissions by design.
        _ = emission


class UniformAgent:
    """Always reports uniform belief, ignoring emissions.

    The "always-50%" adversarial (generalised to 3 states: 1/3 on each).
    Belief never moves. Catches the case where an agent has no
    discriminative power despite being technically a calibrated
    probability distribution.
    """

    def __init__(self) -> None:
        self._belief: Belief = dict.fromkeys(STATES, 1.0 / len(STATES))
        self.name = "UniformAgent"

    @property
    def belief(self) -> Belief:
        return dict(self._belief)

    def observe(self, emission: Emission) -> None:
        # Ignores emissions by design.
        _ = emission


class BayesianAgent:
    """Updates belief via Bayes on each emission, using the toy's likelihoods.

    Same shape as the Bayesian believer in `run_two_believers`. Starts from
    a user-supplied prior and updates with `synthetic_market.update`, which
    multiplies prior by likelihood and renormalises. Honest, calibrated,
    Cromwell-respecting.
    """

    def __init__(self, prior: Belief, name: str = "BayesianAgent") -> None:
        prior_sum = sum(prior.values())
        if not 0.999 < prior_sum < 1.001:
            raise ValueError(f"prior must sum to 1 (got {prior_sum})")
        if any(p <= 0.0 for p in prior.values()):
            raise ValueError("prior must assign strictly positive mass to every state (Cromwell)")
        self._belief: Belief = dict(prior)
        self.name = name

    @property
    def belief(self) -> Belief:
        return dict(self._belief)

    def observe(self, emission: Emission) -> None:
        self._belief = update(self._belief, emission)


def print_agent_introductions() -> None:
    """Show each agent's initial belief and its response to one emission.

    The broken agents (ConfidentAgent, UniformAgent) should produce
    identical belief rows before and after the emission — they ignore it.
    The BayesianAgent should shift toward strengthening on a `strong`
    emission, mirroring the math walked through in Stone 15 Step 2.
    """
    confidently_wrong = ConfidentAgent("decaying", confidence=0.95)
    uniform = UniformAgent()
    bayesian = BayesianAgent(STONE_11A_AGENT_PRIOR, name="BayesianAgent(Stone 11a prior)")

    agents: list[Agent] = [confidently_wrong, uniform, bayesian]

    header = f"{'agent':<42} | {'P(strg)':>8} | {'P(stbl)':>8} | {'P(dec)':>8}"

    print("\nAgent introductions — initial beliefs (before any emission)")
    print(header)
    print("-" * len(header))
    for agent in agents:
        b = agent.belief
        print(
            f"{agent.name:<42} | "
            f"{b['strengthening']:>8.3f} | "
            f"{b['stable']:>8.3f} | "
            f"{b['decaying']:>8.3f}"
        )

    emission: Emission = "strong"
    print(f"\nAfter one '{emission}' emission")
    print(header)
    print("-" * len(header))
    for agent in agents:
        agent.observe(emission)
        b = agent.belief
        print(
            f"{agent.name:<42} | "
            f"{b['strengthening']:>8.3f} | "
            f"{b['stable']:>8.3f} | "
            f"{b['decaying']:>8.3f}"
        )


def print_single_episode_demo(
    truth: CompanyState = "strengthening",
    n_emissions: int = 12,
    seed: int = 42,
) -> None:
    """Run three adversarial agents plus the market through one episode.

    Truth defaults to `strengthening` so the ConfidentAgent (which is
    confident on `decaying`) ends the episode confidently wrong on truth.
    The Bayesian agent uses the Stone 11a agent prior (leans strengthening),
    the market uses the Stone 11a market prior (leans decaying).

    Two outputs:
      - Per-tick belief on the truth state for all four (agents + market).
        You can read down the column to see the trajectory.
      - End-of-episode scoreboard at tick `n_emissions` — Brier, log_score,
        and belief_delta_on_truth (vs the market) for each agent.
    """
    rng = random.Random(seed)

    confident = ConfidentAgent("decaying", confidence=0.95)
    uniform = UniformAgent()
    bayesian = BayesianAgent(STONE_11A_AGENT_PRIOR, name="BayesianAgent")
    market = BayesianAgent(STONE_11A_MARKET_PRIOR, name="Market")

    agents: list[Agent] = [confident, uniform, bayesian]

    print(f"\nSingle episode — truth = {truth}, n_emissions = {n_emissions}, seed = {seed}")
    print(f"Each column is the agent's P({truth}) — its allocation on the truth state.")
    traj_header = (
        f"{'tick':>4} | {'emission':<8} | "
        f"{'Confident':>9} | {'Uniform':>8} | "
        f"{'Bayesian':>9} | {'Market':>8}"
    )
    print(traj_header)
    print("-" * len(traj_header))
    print(
        f"{0:>4} | {'(prior)':<8} | "
        f"{confident.belief[truth]:>9.3f} | "
        f"{uniform.belief[truth]:>8.3f} | "
        f"{bayesian.belief[truth]:>9.3f} | "
        f"{market.belief[truth]:>8.3f}"
    )

    for i in range(1, n_emissions + 1):
        e = sample_emission(truth, rng)
        for a in agents:
            a.observe(e)
        market.observe(e)
        print(
            f"{i:>4} | {e:<8} | "
            f"{confident.belief[truth]:>9.3f} | "
            f"{uniform.belief[truth]:>8.3f} | "
            f"{bayesian.belief[truth]:>9.3f} | "
            f"{market.belief[truth]:>8.3f}"
        )

    print(f"\nEnd-of-episode scoreboard (tick {n_emissions}, truth = {truth})")
    sb_header = (
        f"{'agent':<32} | "
        f"{'P_AI(truth)':>11} | {'Brier':>7} | {'log_score':>9} | {'gap on truth':>12}"
    )
    print(sb_header)
    print("-" * len(sb_header))
    market_belief = market.belief
    all_actors: list[Agent] = [confident, uniform, bayesian, market]
    for a in all_actors:
        b = a.belief
        br = brier(b, truth)
        ls = log_score(b, truth)
        gap = belief_delta_on_truth(b, market_belief, truth)
        print(f"{a.name:<32} | {b[truth]:>11.3f} | {br:>7.3f} | {ls:>9.3f} | {gap:>+12.3f}")


@dataclass(frozen=True)
class AgentMeans:
    """Per-agent aggregate scores across N episodes.

    Returned (as a dict keyed by agent name) by `aggregate_n_episodes`.
    Used by both `run_multi_episode_demo` (the printed display) and the
    integration test in `tests/integration/test_evaluator_ranks_adversaries.py`.
    """

    name: str
    mean_brier: float
    mean_log_score: float
    mean_gap: float
    n_episodes: int


def aggregate_n_episodes(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> tuple[dict[CompanyState, int], dict[str, AgentMeans]]:
    """Run N episodes; return (truth_counts, per_agent_means).

    Each episode picks a random truth uniformly over the 3 states, uses a
    fresh emission seed (`base_seed + episode_idx + 1`), and scores each
    agent's final belief against the chosen truth via Brier, log_score,
    and belief_delta_on_truth (vs the market's belief).

    Deterministic — same arguments produce the exact same results. This
    function is the data source for both `run_multi_episode_demo` (printed
    display) and the integration tests (PYRAMID.md Stone 17). Both consume
    this function, so the numbers in the demo and the asserts always agree.
    """
    truth_rng = random.Random(base_seed)
    truth_choices: list[CompanyState] = list(STATES)
    truth_counts: dict[CompanyState, int] = dict.fromkeys(truth_choices, 0)

    agent_names = [
        "ConfidentAgent(decaying, p=0.95)",
        "UniformAgent",
        "BayesianAgent",
        "Market",
    ]
    raw_scores: dict[str, dict[str, list[float]]] = {
        name: {"brier": [], "log_score": [], "gap": []} for name in agent_names
    }

    for episode_idx in range(n_episodes):
        truth = truth_rng.choice(truth_choices)
        truth_counts[truth] += 1
        episode_seed = base_seed + episode_idx + 1

        confident = ConfidentAgent("decaying", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(STONE_11A_AGENT_PRIOR, name="BayesianAgent")
        market = BayesianAgent(STONE_11A_MARKET_PRIOR, name="Market")
        all_actors: list[Agent] = [confident, uniform, bayesian, market]

        rng = random.Random(episode_seed)
        for _ in range(n_emissions_per_episode):
            e = sample_emission(truth, rng)
            for a in all_actors:
                a.observe(e)

        market_belief = market.belief
        for a in all_actors:
            b = a.belief
            raw_scores[a.name]["brier"].append(brier(b, truth))
            raw_scores[a.name]["log_score"].append(log_score(b, truth))
            raw_scores[a.name]["gap"].append(belief_delta_on_truth(b, market_belief, truth))

    per_agent: dict[str, AgentMeans] = {
        name: AgentMeans(
            name=name,
            mean_brier=sum(raw_scores[name]["brier"]) / n_episodes,
            mean_log_score=sum(raw_scores[name]["log_score"]) / n_episodes,
            mean_gap=sum(raw_scores[name]["gap"]) / n_episodes,
            n_episodes=n_episodes,
        )
        for name in agent_names
    }

    return truth_counts, per_agent


def run_multi_episode_demo(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> None:
    """Print the per-agent summary from `aggregate_n_episodes`.

    Thin wrapper over `aggregate_n_episodes`. The integration test consumes
    `aggregate_n_episodes` directly to assert on the same numbers.

    Expected ranking on Brier and log_score:
      BayesianAgent (best) < UniformAgent (middle) < ConfidentAgent (worst)

    ConfidentAgent does fine on the ~1/3 of episodes where truth happens to
    be `decaying`; on the other ~2/3 it scores catastrophically. UniformAgent's
    Brier is constant at 0.667 by symmetry. BayesianAgent generally
    converges close to truth; its mean should be visibly lowest.
    """
    truth_counts, per_agent = aggregate_n_episodes(
        n_episodes=n_episodes,
        n_emissions_per_episode=n_emissions_per_episode,
        base_seed=base_seed,
    )

    print(
        f"\nMulti-episode summary — {n_episodes} episodes, "
        f"{n_emissions_per_episode} emissions each, base_seed = {base_seed}"
    )
    truth_dist = ", ".join(f"{state}: {count}" for state, count in truth_counts.items())
    print(f"Truth distribution across episodes: {truth_dist}")

    header = f"{'agent':<32} | {'mean Brier':>10} | {'mean log_sc':>11} | {'mean gap':>10}"
    print(header)
    print("-" * len(header))

    for means in per_agent.values():
        print(
            f"{means.name:<32} | "
            f"{means.mean_brier:>10.3f} | "
            f"{means.mean_log_score:>11.3f} | "
            f"{means.mean_gap:>+10.3f}"
        )


if __name__ == "__main__":
    print_agent_introductions()
    # ConfidentAgent's UNLUCKY case: truth = strengthening, agent is confident on
    # decaying. Confident scores catastrophically; well-calibrated wins clearly.
    print_single_episode_demo(truth="strengthening", seed=42)
    # ConfidentAgent's LUCKY case: truth = decaying, agent is confident on the
    # correct state. Confident scores GREAT on this single episode — looks like
    # a genius. The aggregate (next demo) shows it doesn't matter.
    print_single_episode_demo(truth="decaying", seed=42)
    run_multi_episode_demo()
