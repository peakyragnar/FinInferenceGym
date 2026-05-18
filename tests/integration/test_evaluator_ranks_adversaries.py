"""Stone 17: the evaluator ranks adversarial agents correctly across episodes.

Property under test:

  Across N episodes with randomized truth and seed, the per-agent mean
  scores order as

      BayesianAgent < UniformAgent < ConfidentAgent      (Brier, log_score)

  (lower = better). And:

    - UniformAgent's mean Brier is exactly 2/3 by symmetry — for any
      truth distribution in a 3-state hypothesis space.

PYRAMID.md Stone 16 demonstrates the property by inspection;
this file (Stone 17) locks it in as a CI gate. Any future change to the
evaluator, the toy world, or the adversarial agents that breaks the
ordering will fail this test.

The pre-v5 "Market" parallel agent and `mean_gap` (belief-delta-on-truth)
tests were removed by the Constitution v5 cleanup pass alongside the
`belief_delta_on_truth` scoring function and the Stone 11a market-belief
priors. New v5 integration tests for the Forecast Ledger reliability and
calibration shrinkage land when those stones are taught.
"""

from __future__ import annotations

import pytest

from fingym.toys.adversarial_agents import AgentMeans, aggregate_n_episodes

# Agent names as emitted by aggregate_n_episodes. Kept as constants so
# renaming in one place is the only change required to keep tests valid.
CONFIDENT = "ConfidentAgent(decaying, p=0.95)"
UNIFORM = "UniformAgent"
BAYESIAN = "BayesianAgent"


@pytest.fixture(scope="module")
def per_agent() -> dict[str, AgentMeans]:
    """100-episode aggregate at base_seed=42, computed once per module."""
    _, per_agent_means = aggregate_n_episodes(
        n_episodes=100, n_emissions_per_episode=12, base_seed=42
    )
    return per_agent_means


def test_brier_ranks_bayesian_uniform_confident(
    per_agent: dict[str, AgentMeans],
) -> None:
    """Mean Brier: BayesianAgent << UniformAgent << ConfidentAgent."""
    assert per_agent[BAYESIAN].mean_brier < per_agent[UNIFORM].mean_brier
    assert per_agent[UNIFORM].mean_brier < per_agent[CONFIDENT].mean_brier


def test_log_score_ranks_bayesian_uniform_confident(
    per_agent: dict[str, AgentMeans],
) -> None:
    """Mean log_score: BayesianAgent << UniformAgent << ConfidentAgent."""
    assert per_agent[BAYESIAN].mean_log_score < per_agent[UNIFORM].mean_log_score
    assert per_agent[UNIFORM].mean_log_score < per_agent[CONFIDENT].mean_log_score


def test_uniform_mean_brier_equals_theoretical_baseline(
    per_agent: dict[str, AgentMeans],
) -> None:
    """UniformAgent's mean Brier is 2/3 by symmetry, exactly.

    For a uniform belief {1/3, 1/3, 1/3} in a 3-state space, Brier evaluates
    to (1/3)^2 + (1/3)^2 + (2/3)^2 = 6/9 = 2/3 for ANY truth state. So the
    per-episode Brier is constant; the mean across N episodes is also 2/3
    regardless of how the truth distributes.
    """
    expected = 2.0 / 3.0
    assert abs(per_agent[UNIFORM].mean_brier - expected) < 1e-9
