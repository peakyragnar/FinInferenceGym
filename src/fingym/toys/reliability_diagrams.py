"""reliability_diagrams.py — Stone 18 visual exit criterion for Phase 0.

Generates an HTML reliability-diagram figure for the three adversarial
agents (ConfidentAgent, UniformAgent, BayesianAgent). Per-state pooling:
for each agent and each (episode, tick, state) triple across N episodes,
records (claim = agent's claimed P(state), outcome = 1 if truth == state
else 0). Buckets the claims and plots (mean_claim, observed_rate) per
bucket against the 45° calibration line.

Expected visual shapes (PYRAMID.md Stone 18, BUILD.md Phase 0 exit):

  - ConfidentAgent: two clusters. Points at (~0.025, ~0.33) and
    (~0.95, ~0.34). Both far off the diagonal in opposite directions.
  - UniformAgent: one point near (0.333, 0.333). On the diagonal but
    only ONE bucket populated — no discrimination across confidence
    levels.
  - BayesianAgent: many buckets populated, points close to the
    diagonal — discrimination AND calibration.

Under Constitution v5 the pre-v5 "Market" parallel agent was removed
from this demo (it was a Stone 11a parallel believer used to compute
the belief-delta gap; the v5 framing isolates the Market-State Baseline
in its own module — `src/fingym/baseline/` — and the reliability diagrams
focus on per-agent calibration).

Run: `uv run python -m fingym.toys.reliability_diagrams`

The HTML is self-contained (embedded plotly.js) — opens in any browser.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from plotly import graph_objects as go
from plotly.subplots import make_subplots

from fingym.evaluator.scoring import ReliabilityBucket, reliability_buckets
from fingym.toys.adversarial_agents import (
    DEFAULT_BAYESIAN_PRIOR,
    Agent,
    BayesianAgent,
    ConfidentAgent,
    UniformAgent,
)
from fingym.toys.synthetic_market import (
    STATES,
    CompanyState,
    sample_emission,
)

if TYPE_CHECKING:
    pass


def collect_per_state_predictions(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> dict[str, tuple[list[float], list[int]]]:
    """Run N episodes; gather per-state (claim, outcome) pairs per agent.

    For each agent and each (episode, tick, state) triple, records:
      - claim: agent's claimed P(state) at that tick
      - outcome: 1 if that episode's truth was `state`, else 0

    Per-state pooling gives 3 predictions per agent per tick. Across
    100 episodes x 12 ticks x 3 states = 3600 predictions per agent.
    Deterministic given `base_seed`.
    """
    truth_rng = random.Random(base_seed)
    truth_choices: list[CompanyState] = list(STATES)

    agent_names = [
        "ConfidentAgent(decaying, p=0.95)",
        "UniformAgent",
        "BayesianAgent",
    ]
    per_agent: dict[str, tuple[list[float], list[int]]] = {name: ([], []) for name in agent_names}

    for episode_idx in range(n_episodes):
        truth = truth_rng.choice(truth_choices)
        episode_seed = base_seed + episode_idx + 1

        confident = ConfidentAgent("decaying", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
        all_actors: list[Agent] = [confident, uniform, bayesian]

        rng = random.Random(episode_seed)
        for _ in range(n_emissions_per_episode):
            e = sample_emission(truth, rng)
            for a in all_actors:
                a.observe(e)
                claims, outcomes = per_agent[a.name]
                belief = a.belief
                for state in STATES:
                    claims.append(belief[state])
                    outcomes.append(1 if truth == state else 0)

    return per_agent


def compute_reliability_data(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
    n_buckets: int = 10,
) -> dict[str, list[ReliabilityBucket]]:
    """Run predictions + bucketing; return per-agent reliability buckets."""
    per_agent_preds = collect_per_state_predictions(
        n_episodes=n_episodes,
        n_emissions_per_episode=n_emissions_per_episode,
        base_seed=base_seed,
    )
    return {
        name: reliability_buckets(claims, outcomes, n_buckets=n_buckets)
        for name, (claims, outcomes) in per_agent_preds.items()
    }


def render_reliability_html(
    output_path: Path,
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
    n_buckets: int = 10,
) -> Path:
    """Generate the HTML reliability-diagram figure and write to output_path.

    Self-contained HTML (embedded plotly.js). Four panels in a 2x2 grid:
    one per agent. Each panel has the 45° calibration line and the per-
    bucket scatter, sized by bucket count, hover-styled with details.
    """
    reliability = compute_reliability_data(
        n_episodes=n_episodes,
        n_emissions_per_episode=n_emissions_per_episode,
        base_seed=base_seed,
        n_buckets=n_buckets,
    )

    agent_order = [
        "ConfidentAgent(decaying, p=0.95)",
        "UniformAgent",
        "BayesianAgent",
    ]

    fig: Any = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=agent_order,
        horizontal_spacing=0.10,
    )

    for idx, name in enumerate(agent_order):
        row = 1
        col = idx + 1
        buckets = reliability[name]

        # 45° calibration reference line
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                line={"color": "gray", "dash": "dash", "width": 1},
                name="perfect calibration",
                showlegend=(idx == 0),
            ),
            row=row,
            col=col,
        )

        # Bucket scatter
        mean_claims = [b.mean_claim for b in buckets]
        observed_rates = [b.observed_rate for b in buckets]
        counts = [b.count for b in buckets]
        hover_text = [
            f"bucket [{b.lo:.2f}, {b.hi:.2f})<br>"
            f"mean claim: {b.mean_claim:.3f}<br>"
            f"observed rate: {b.observed_rate:.3f}<br>"
            f"count: {b.count}"
            for b in buckets
        ]

        fig.add_trace(
            go.Scatter(
                x=mean_claims,
                y=observed_rates,
                mode="markers",
                marker={
                    "size": [min(40, 8 + c / 50) for c in counts],
                    "color": "steelblue",
                    "line": {"color": "black", "width": 1},
                },
                hovertext=hover_text,
                hoverinfo="text",
                name=name,
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        fig.update_xaxes(range=[0, 1], title_text="claimed P(state)", row=row, col=col)
        fig.update_yaxes(range=[0, 1], title_text="observed frequency", row=row, col=col)

    fig.update_layout(
        title=(
            f"Reliability Diagrams — Stone 18, Phase 0 Exit Criterion "
            f"(N={n_episodes} episodes x {n_emissions_per_episode} ticks "
            f"x 3 states, seed={base_seed})"
        ),
        height=900,
        width=1100,
        showlegend=True,
        legend={"x": 0.02, "y": 1.08, "orientation": "h"},
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="inline")
    return output_path


if __name__ == "__main__":
    # Default output: <repo_root>/notebooks/reliability_diagrams.html.
    repo_root = Path(__file__).resolve().parents[3]
    out = repo_root / "notebooks" / "reliability_diagrams.html"
    saved = render_reliability_html(out)
    print(f"\nReliability diagrams written to: {saved}")
    print("Open in a browser to inspect the visual exit criterion.")
