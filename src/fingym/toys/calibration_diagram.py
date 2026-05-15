"""calibration_diagram.py — runnable visualization of Stone 8.

Three adversarial agents make 200 predictions on binary events with mixed
true probabilities. For each agent, prints a reliability table showing how
its claimed confidence compares to what actually happened, grouped into
10% buckets. The three agents produce three visibly different signatures.

Same pattern as the weather-forecaster example: count, group, compare,
weight, average. No formulas; just arithmetic on real data.

Agents:
  - W (well-calibrated): claims the true probability of each event.
    Reality in each bucket matches the claim. Low calibration error.
  - O (confidently-wrong): pushes claims to extremes (10% or 90%).
    Reality in each bucket is more middle-ground than the claim. High error.
  - U (always-50%): ignores everything and always claims 50%. All
    events land in one bucket. Calibrated only if the base rate is 50%;
    miscalibrated otherwise.

Run: uv run python -m fingym.toys.calibration_diagram
"""

import random
from collections.abc import Callable

# A binary event: (true probability, actual outcome 0 or 1).
type Event = tuple[float, int]

# An agent maps the true probability to its stated probability.
# (Real agents would see evidence, not the true probability. Here we feed
# them the true probability so each one's "personality" — calibrated,
# overconfident, uninformative — can be expressed cleanly.)
type Agent = Callable[[float], float]


# --- Three agents ---------------------------------------------------------


def well_calibrated(true_p: float) -> float:
    """Says the true probability. Calibrated by construction."""
    return true_p


def confidently_wrong(true_p: float) -> float:
    """Pushes everything to extremes. Overconfident on both sides."""
    return 0.9 if true_p > 0.5 else 0.1


def always_fifty(true_p: float) -> float:
    """Always says 50%. Calibrated only if the base rate equals 50%."""
    return 0.5


# --- Generate the test set ------------------------------------------------


def generate_events(n: int = 200, seed: int = 42) -> list[Event]:
    """Generate n binary events with varying true probabilities.

    True probabilities are chosen uniformly from {0.4, 0.6, 0.8}.
    Base rate (the average true probability) is therefore 0.6.
    Each event's outcome is sampled from its true probability.
    """
    rng = random.Random(seed)
    true_probs = [0.4, 0.6, 0.8]
    events: list[Event] = []
    for _ in range(n):
        p = rng.choice(true_probs)
        y = 1 if rng.random() < p else 0
        events.append((p, y))
    return events


# --- Bucketing and per-bucket statistics ----------------------------------


def bucket_index(claim: float, n_buckets: int = 10) -> int:
    """Map a claim in [0, 1] to a bucket index in [0, n_buckets-1]."""
    if claim >= 1.0:
        return n_buckets - 1
    return int(claim * n_buckets)


def bucket_label(b: int, n_buckets: int = 10) -> str:
    """Human-readable label for bucket b."""
    low = b * 100 // n_buckets
    high = (b + 1) * 100 // n_buckets
    return f"[{low:>2}%, {high:>3}%)"


def print_reliability_table(agent_name: str, agent: Agent, events: list[Event]) -> float:
    """Print the reliability table for one agent. Return its calibration error."""
    # Compute the agent's claim for each event.
    claim_outcome_pairs: list[tuple[float, int]] = [(agent(p), y) for p, y in events]

    # Group by bucket.
    buckets: dict[int, list[tuple[float, int]]] = {}
    for claim, outcome in claim_outcome_pairs:
        b = bucket_index(claim)
        buckets.setdefault(b, []).append((claim, outcome))

    # Print header.
    print(f"\n=== {agent_name} ===")
    print(
        f"{'Claim bucket':<14}  {'# events':>9}  {'Mean claim':>11}  "
        f"{'Observed':>10}  {'Gap':>8}  {'Weighted':>10}"
    )
    print("-" * 75)

    # Compute per-bucket stats and ECE.
    total_weighted_gap = 0.0
    total_events = 0
    for b in sorted(buckets):
        rows = buckets[b]
        n = len(rows)
        mean_claim = sum(claim for claim, _ in rows) / n
        observed_rate = sum(outcome for _, outcome in rows) / n
        gap = abs(mean_claim - observed_rate)
        weighted_contribution = n * gap

        total_weighted_gap += weighted_contribution
        total_events += n

        print(
            f"{bucket_label(b):<14}  {n:>9}  {mean_claim * 100:>10.1f}%  "
            f"{observed_rate * 100:>9.1f}%  {gap * 100:>7.1f}  "
            f"{weighted_contribution * 100:>9.1f}"
        )

    print("-" * 75)
    ece = total_weighted_gap / total_events
    print(
        f"{'TOTAL':<14}  {total_events:>9}  {'':>11}  {'':>10}  {'':>8}  "
        f"{total_weighted_gap * 100:>9.1f}"
    )
    print(f"Calibration error (ECE) = {ece * 100:.2f} percentage points")
    return ece


# --- Main ----------------------------------------------------------------


def main() -> None:
    events = generate_events()

    print(
        "200 binary events. True probabilities drawn from {40%, 60%, 80%}\n"
        "(uniformly). Base rate (average truth) is therefore 60%."
    )

    ece_w = print_reliability_table(
        "Agent W — well-calibrated (says true probability)",
        well_calibrated,
        events,
    )

    ece_o = print_reliability_table(
        "Agent O — confidently-wrong (claims 90% or 10%)",
        confidently_wrong,
        events,
    )

    ece_u = print_reliability_table(
        "Agent U — always-50% (ignores evidence)",
        always_fifty,
        events,
    )

    print("\n=== Summary — one row per agent ===")
    print(f"{'Agent':<35}  {'Calibration error':>20}")
    print("-" * 58)
    print(f"{'W (well-calibrated)':<35}  {ece_w * 100:>17.2f} pp")
    print(f"{'O (confidently-wrong)':<35}  {ece_o * 100:>17.2f} pp")
    print(f"{'U (always-50%)':<35}  {ece_u * 100:>17.2f} pp")

    print(
        "\n"
        "Interpretation:\n"
        "  W is calibrated. In each bucket, what it claimed matches what\n"
        "  reality delivered. The 40% bucket actually had ~40% positives,\n"
        "  the 60% bucket had ~60%, the 80% bucket had ~80%. Small gaps.\n"
        "\n"
        "  O pushes claims to extremes (10% or 90%) but reality in those\n"
        "  buckets is closer to the middle. When it claims 90%, only ~70%\n"
        "  of those events were positives. When it claims 10%, ~40% were\n"
        "  positives. Big gaps in both directions. Calibration error highest.\n"
        "\n"
        "  U always says 50%. Every event lands in the 50% bucket. Reality\n"
        "  in that bucket is the base rate (60% in this simulation). Gap is\n"
        "  the difference between 50% and 60% — only 10 percentage points.\n"
        "  U LOOKS calibrated in a single number, but it is not useful: it\n"
        "  cannot distinguish a 40% event from an 80% event. Layer-1 scoring\n"
        "  rules (Brier, log score) would flag U as bad even though its\n"
        "  calibration number is mild. Calibration alone is necessary, not\n"
        "  sufficient — the agent also needs to distinguish (discriminate)\n"
        "  between high-probability and low-probability events.\n"
    )


if __name__ == "__main__":
    main()
