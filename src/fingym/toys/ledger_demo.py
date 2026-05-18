"""ledger_demo.py — Cluster A: read the Forecast Ledger by hand.

Runs 100 episodes through the three adversarial agents (Confident, Uniform,
Bayesian); records each agent's final per-episode forecast into a shared
ForecastLedger keyed by `signal_class_id`; then prints the three
per-signal-class reliability tables.

This is the human-eyeballing inspection surface — the same data the
integration test in `tests/integration/test_forecast_ledger_cluster_a.py`
asserts properties on, but printed in tables so an auditor can read the
Ledger by hand.

Phase 1 NEW Cluster A artifact. Companion to:
  - synthetic_market.py — the toy world (states, emissions, realized
    returns mapped to 5 buckets)
  - adversarial_agents.py — Confident / Uniform / Bayesian agents
  - contract_emitter.py — Stone 19 Contract demo
  - reliability_diagrams.py — Stone 18 visual demo (per-tick pooling)

Run: `uv run python -m fingym.toys.ledger_demo`
"""

from __future__ import annotations

import random

from fingym.ledger.forecast_ledger import ForecastLedger
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
    realize_return_at_horizon,
    return_to_bucket,
    sample_emission,
)

SIGNAL_CLASS_LABELS: dict[str, str] = {
    "confident_static": "ConfidentAgent — always 95% on below_minus_5, no matter the evidence",
    "uniform_static": "UniformAgent — always 0.2 per bucket, never updates",
    "bayesian_3state_toy": "BayesianAgent — updates on each emission",
}


def populate_ledger(
    n_episodes: int = 100,
    n_emissions_per_episode: int = 12,
    base_seed: int = 42,
) -> ForecastLedger:
    """Run N episodes; record each agent's final forecast into a shared Ledger."""
    state_rng = random.Random(base_seed)
    state_choices: list[CompanyState] = list(STATES)
    ledger = ForecastLedger()

    for episode_idx in range(n_episodes):
        truth_state = state_rng.choice(state_choices)
        episode_seed = base_seed + episode_idx + 1
        episode_rng = random.Random(episode_seed)

        confident = ConfidentAgent("below_minus_5", confidence=0.95)
        uniform = UniformAgent()
        bayesian = BayesianAgent(DEFAULT_BAYESIAN_PRIOR, name="BayesianAgent")
        all_actors: list[Agent] = [confident, uniform, bayesian]

        for _ in range(n_emissions_per_episode):
            emission = sample_emission(truth_state, episode_rng)
            for a in all_actors:
                a.observe(emission)

        realized_return = realize_return_at_horizon(truth_state, episode_rng)
        realized_bucket = return_to_bucket(realized_return)

        for a in all_actors:
            ledger.record(a.signal_class_id, a.forecast, realized_bucket)

    return ledger


def _gap_label(gap: float) -> str:
    """Directional reading of (claim - observed). >0.05 = overconfident,
    <-0.05 = underconfident, otherwise calibrated within sample noise."""
    if gap > 0.05:
        return "overconfident"
    if gap < -0.05:
        return "underconfident"
    return "calibrated"


def print_reliability_table(
    ledger: ForecastLedger,
    signal_class_id: str,
    *,
    n_buckets: int = 10,
) -> None:
    """Print one per-signal-class reliability table.

    Columns: claim range | avg claim | observed | count | gap | label.
    `gap = avg_claim - observed_rate`; positive = overconfident, negative =
    underconfident.
    """
    label = SIGNAL_CLASS_LABELS.get(signal_class_id, "")
    n_records = ledger.records_for_signal_class(signal_class_id)
    print(f"  signal_class_id = {signal_class_id}")
    print(f"  ({label})")
    print(f"  forecasts recorded: {n_records}")
    print()

    buckets = ledger.reliability_for_signal_class(signal_class_id, n_buckets=n_buckets)
    if not buckets:
        print("    (no entries)")
        print()
        return

    print(
        f"    {'claim range':<13} {'avg claim':>10} {'observed':>10} "
        f"{'count':>7} {'gap':>8}  {'label'}"
    )
    print(f"    {'-' * 13} {'-' * 10} {'-' * 10} {'-' * 7} {'-' * 8}  {'-' * 14}")
    for b in buckets:
        gap = b.mean_claim - b.observed_rate
        gap_str = f"{gap:+.3f}"
        range_str = f"[{b.lo:.2f}, {b.hi:.2f})"
        print(
            f"    {range_str:<13} {b.mean_claim:>10.3f} {b.observed_rate:>10.3f} "
            f"{b.count:>7} {gap_str:>8}  {_gap_label(gap)}"
        )
    print()


def main() -> None:
    """Print the three Cluster A reliability tables."""
    print()
    print("=" * 78)
    print("  Cluster A — Forecast Ledger inspection")
    print("=" * 78)
    print(
        "  100 episodes. Each agent's FINAL per-episode forecast over the 5 return\n"
        "  buckets is recorded into a shared Ledger, indexed by signal_class_id.\n"
        "  Each table below is the Ledger's read API answering: 'across all your\n"
        "  forecasts in this signal class, when you claimed X% on some bucket, what\n"
        "  fraction of those claims actually realized that bucket?'\n"
        "\n"
        "  - 'gap' = avg claim - observed rate. Positive = overconfident.\n"
        "    Negative = underconfident. Near zero = on the calibration diagonal.\n"
    )
    print("=" * 78)
    print()

    ledger = populate_ledger()
    for sci in ("confident_static", "uniform_static", "bayesian_3state_toy"):
        print_reliability_table(ledger, sci)
        print("-" * 78)
        print()


if __name__ == "__main__":
    main()
