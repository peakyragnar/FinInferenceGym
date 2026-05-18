"""reliability_diagrams.py — Stone 18 visual exit criterion for Phase 0.

Generates an HTML reliability-diagram figure for the three adversarial agents
(ConfidentAgent, UniformAgent, BayesianAgent). Per-bucket pooling: for each
agent and each (episode, tick, bucket) triple across N episodes, records
(claim = agent's claimed P(bucket), outcome = 1 if the episode's realized log
return falls in that bucket, else 0). Buckets the claims and plots
(mean_claim, observed_rate) per bucket against the 45° calibration line.

Expected visual shapes (PYRAMID.md Stone 18, BUILD.md Phase 0 exit, updated
under Phase 1 NEW Cluster A):

  - ConfidentAgent: two clusters. A high-claim point at (~0.95, observed-rate-
    of-the-confident-bucket-across-episodes) and a low-claim point at
    (~0.0125, observed-rate-of-the-other-buckets). Both far off the diagonal.
  - UniformAgent: one point at (0.2, 0.2). On the diagonal but only ONE bucket
    populated — no discrimination across confidence levels.
  - BayesianAgent: many buckets populated, points close to the diagonal —
    discrimination AND calibration.

Under v5 the agent's hypothesis space is realized-return buckets, NOT hidden
states. The realized bucket per episode is drawn from the state-conditional
return distribution at horizon and serves as the binary outcome for the
per-bucket calibration check.

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
    RETURN_BUCKETS,
    STATES,
    CompanyState,
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
)

if TYPE_CHECKING:
    pass


def collect_per_bucket_predictions(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> dict[str, tuple[list[float], list[int]]]:
    """Run N episodes; gather per-bucket (claim, outcome) pairs per agent.

    For each agent and each (episode, tick, bucket) triple, records:
      - claim: agent's claimed P(bucket) at that tick
      - outcome: 1 if the episode's realized return falls in that bucket, else 0

    Per-bucket pooling gives N_BUCKETS predictions per agent per tick. Across
    100 episodes x 12 ticks x 5 buckets = 6000 predictions per agent.
    Deterministic given `base_seed`.
    """
    state_rng = random.Random(base_seed)
    state_choices: list[CompanyState] = list(STATES)

    agent_names = [
        "ConfidentAgent(below_minus_5, p=0.95)",
        "UniformAgent",
        "BayesianAgent",
    ]
    per_agent: dict[str, tuple[list[float], list[int]]] = {name: ([], []) for name in agent_names}

    for episode_idx in range(n_episodes):
        truth_state = state_rng.choice(state_choices)
        episode_seed = base_seed + episode_idx + 1
        episode_rng = random.Random(episode_seed)

        confident = ConfidentAgent("below_minus_5", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
        all_actors: list[Agent] = [confident, uniform, bayesian]

        # Realize the return for this episode upfront so we know the outcome bucket.
        # The agents never see it; the rng has already been advanced for the
        # emission stream below.
        emissions = [
            sample_emission(truth_state, episode_rng) for _ in range(n_emissions_per_episode)
        ]
        realized_log_return = realize_return_at_horizon(truth_state, episode_rng)
        realized_bucket = return_to_bucket(realized_log_return)

        for emission in emissions:
            for a in all_actors:
                a.observe(emission)
                claims, outcomes = per_agent[a.name]
                forecast = a.forecast
                for bucket in RETURN_BUCKETS:
                    claims.append(forecast[bucket])
                    outcomes.append(1 if bucket == realized_bucket else 0)

    return per_agent


def compute_reliability_data(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
    n_buckets: int = 10,
) -> dict[str, list[ReliabilityBucket]]:
    """Run predictions + bucketing; return per-agent reliability buckets."""
    per_agent_preds = collect_per_bucket_predictions(
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

    Self-contained HTML (embedded plotly.js). Three panels in a row, one per
    agent. Each panel has the 45° calibration line and the per-claim-bucket
    scatter, sized by bucket count, hover-styled with details.
    """
    reliability = compute_reliability_data(
        n_episodes=n_episodes,
        n_emissions_per_episode=n_emissions_per_episode,
        base_seed=base_seed,
        n_buckets=n_buckets,
    )

    agent_order = [
        "ConfidentAgent(below_minus_5, p=0.95)",
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
            f"claim bucket [{b.lo:.2f}, {b.hi:.2f})<br>"
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

        fig.update_xaxes(range=[0, 1], title_text="claimed P(bucket)", row=row, col=col)
        fig.update_yaxes(range=[0, 1], title_text="observed frequency", row=row, col=col)

    fig.update_layout(
        title=(
            f"Reliability Diagrams — Stone 18, Phase 0 Exit Criterion "
            f"(N={n_episodes} episodes x {n_emissions_per_episode} ticks x "
            f"{len(RETURN_BUCKETS)} buckets, seed={base_seed})"
        ),
        height=600,
        width=1400,
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
