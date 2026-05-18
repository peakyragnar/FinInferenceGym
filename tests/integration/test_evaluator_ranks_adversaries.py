"""Stone 17: the evaluator ranks adversarial agents correctly across episodes.

Property under test:

  Across N episodes with randomized state and seed, the per-agent mean scores
  order as

      BayesianAgent < UniformAgent < ConfidentAgent      (Brier, log_score)

  (lower = better). And:

    - UniformAgent's mean Brier is exactly (N-1)/N by symmetry. For 5 buckets,
      that's 4/5 = 0.8. The per-episode Brier is constant; the mean across N
      episodes is also 4/5 regardless of how the realized bucket distributes.

PYRAMID.md Stone 16 demonstrates the property by inspection; this file (Stone 17)
locks it in as a CI gate. Any future change to the evaluator, the toy world,
or the adversarial agents that breaks the ordering will fail this test.

Phase 1 NEW Cluster A: agents now emit forecasts over realized-return BUCKETS
(not state beliefs). UniformAgent's mean Brier is now (N-1)/N = 0.8 for 5
buckets (was 2/3 for 3 states pre-Cluster-A).
"""

from __future__ import annotations

import pytest

from fingym.toys.adversarial_agents import AgentMeans, aggregate_n_episodes
from fingym.toys.synthetic_market import RETURN_BUCKETS

# Agent names as emitted by aggregate_n_episodes. Kept as constants so
# renaming in one place is the only change required to keep tests valid.
CONFIDENT = "ConfidentAgent(below_minus_5, p=0.95)"
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
    """Mean Brier: BayesianAgent < UniformAgent < ConfidentAgent."""
    assert per_agent[BAYESIAN].mean_brier < per_agent[UNIFORM].mean_brier, (
        f"Expected BayesianAgent ({per_agent[BAYESIAN].mean_brier:.3f}) "
        f"< UniformAgent ({per_agent[UNIFORM].mean_brier:.3f})"
    )
    assert per_agent[UNIFORM].mean_brier < per_agent[CONFIDENT].mean_brier, (
        f"Expected UniformAgent ({per_agent[UNIFORM].mean_brier:.3f}) "
        f"< ConfidentAgent ({per_agent[CONFIDENT].mean_brier:.3f})"
    )


def test_log_score_ranks_bayesian_uniform_confident(
    per_agent: dict[str, AgentMeans],
) -> None:
    """Mean log_score: BayesianAgent < UniformAgent < ConfidentAgent."""
    assert per_agent[BAYESIAN].mean_log_score < per_agent[UNIFORM].mean_log_score, (
        f"Expected BayesianAgent ({per_agent[BAYESIAN].mean_log_score:.3f}) "
        f"< UniformAgent ({per_agent[UNIFORM].mean_log_score:.3f})"
    )
    assert per_agent[UNIFORM].mean_log_score < per_agent[CONFIDENT].mean_log_score, (
        f"Expected UniformAgent ({per_agent[UNIFORM].mean_log_score:.3f}) "
        f"< ConfidentAgent ({per_agent[CONFIDENT].mean_log_score:.3f})"
    )


def test_uniform_mean_brier_equals_theoretical_baseline(
    per_agent: dict[str, AgentMeans],
) -> None:
    """UniformAgent's mean Brier is (N-1)/N by symmetry, exactly.

    For a uniform forecast of 1/N over N buckets, with one realized bucket,
    Brier = (1/N - 1)^2 + (N-1) * (1/N)^2 = (N-1)/N. For N=5 buckets, that's
    0.8. Per-episode Brier is constant; the mean across N episodes is also
    (N-1)/N regardless of which buckets are realized.
    """
    n = len(RETURN_BUCKETS)
    expected = (n - 1) / n  # 4/5 = 0.8 for 5 buckets
    assert abs(per_agent[UNIFORM].mean_brier - expected) < 1e-9, (
        f"Expected UniformAgent Brier = {expected}; got {per_agent[UNIFORM].mean_brier}"
    )
