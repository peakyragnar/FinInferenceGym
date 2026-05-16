"""Proper scoring rules.

These are the math primitives of the verification side. They are
architectural physics (DESIGN.md "Architectural Physics") — not search
artifacts — because they uniquely make honesty the dominant strategy.

A scoring rule maps (belief, revealed_outcome) -> a real number that
"scores" the belief. A *proper* scoring rule has the property that, in
expectation, the way to minimise your score is to report your true
belief. Lying about confidence costs more than honesty does. Brier and
log score are the canonical proper scoring rules.

Conventions:
  - Lower is better. Both Brier and log score are losses.
  - A belief is a `dict[H, float]` whose values are non-negative and
    sum to ~1. We do not re-validate that here on every call — beliefs
    come from agent terminal outputs that are validated at the boundary.
    Passing an unnormalised belief is undefined behaviour and will be
    caught at the model-interface layer when that lands.
  - `H` is generic over the hypothesis alphabet (PEP 695). The coin
    toy uses `Coin = Literal["fair", "biased"]`; the 3-state company
    toy will use a 3-element Literal; future state spaces are equally
    fine.

Cromwell's rule (intuitions.md #1) shows up explicitly in log score:
when the belief assigns probability 0 to a hypothesis that turns out
to be the outcome, the score is `+inf`. That is the *correct* loud
signal — a Cromwell violation is what an evaluator should refuse to
forgive. Returning `+inf` propagates the violation rather than hiding
it behind a clipped epsilon (which is what most ML libs do, and which
silently kills the signal).
"""

import math
from dataclasses import dataclass


def brier[H](belief: dict[H, float], outcome: H) -> float:
    """Multi-class Brier score.

        BS = sum_h (belief[h] - indicator[h == outcome])^2

    Range: [0, 2] for K hypotheses (it reaches 2 only on a
    confidently-wrong K=2 prediction). Lower is better. The squaring
    is what makes Brier a *proper* scoring rule — confidently-wrong
    predictions are punished disproportionately more than mildly-wrong
    ones, so on average the way to minimise it is to report your true
    belief.

    A hypothesis that doesn't appear in `belief` is treated as having
    probability 0 — but if that's the outcome, it shows up as a square
    (1 - 0)^2 = 1 *plus* whatever non-zero mass other hypotheses
    received. The Brier penalty for missing the outcome from your
    hypothesis space is the same shape as the penalty for assigning it
    near-zero mass.
    """
    score = 0.0
    seen_outcome = False
    for hypothesis, probability in belief.items():
        indicator = 1.0 if hypothesis == outcome else 0.0
        if hypothesis == outcome:
            seen_outcome = True
        score += (probability - indicator) ** 2
    if not seen_outcome:
        # outcome was not in the belief's support → penalise as full miss
        score += 1.0
    return score


def log_score[H](belief: dict[H, float], outcome: H) -> float:
    """Negative-log-likelihood (log loss) of the outcome under the belief.

        LS = -ln(belief[outcome])

    Range: [0, +inf). Lower is better. Like Brier, this is a proper
    scoring rule.

    Cromwell case: if `belief[outcome]` is missing or 0, the score is
    `+inf`. This is deliberate — a hypothesis assigned probability 0
    that turns out to be the outcome is an unrecoverable inference
    failure under Bayesian updating (no future evidence can resurrect
    it). The scoreboard should make that loud.
    """
    probability = belief.get(outcome, 0.0)
    if probability <= 0.0:
        return math.inf
    return -math.log(probability)


def belief_delta_on_truth[H](p_ai: dict[H, float], p_market: dict[H, float], outcome: H) -> float:
    """Signed gap between agent and market beliefs on the realized outcome.

        delta = P_AI[outcome] - P_market[outcome]

    Range: [-1.0, +1.0]. The Stone 11a per-row metric (PYRAMID.md Stone 11a,
    FORMULAS.md "Market-delta scoring"). Sign reads as:

        > 0  agent more confident on the truth than the market (edge)
        = 0  agreement on the truth (no edge to extract)
        < 0  market more confident on the truth than the agent (anti-edge)

    Unlike Brier and log_score, this is signed — not a loss — and structurally
    independent of Layer-1 calibration: two contracts with identical Brier and
    log_score can have very different belief_delta_on_truth, because Brier and
    log_score never see `P_market`. That independence is exactly why Stone 11a
    earns its own scoreboard column.

    Missing outcome keys in either belief are treated as probability 0.0. The
    gap stays finite regardless; Cromwell loudness lives in log_score.
    """
    return p_ai.get(outcome, 0.0) - p_market.get(outcome, 0.0)


@dataclass(frozen=True)
class ReliabilityBucket:
    """One row of a reliability diagram (PYRAMID.md Stone 8 / Stone 18).

    Returned by `reliability_buckets`. A calibrated agent has
    `mean_claim ≈ observed_rate` in every bucket (points on the 45° line).
    """

    bucket_idx: int
    lo: float
    hi: float
    mean_claim: float
    observed_rate: float
    count: int


def reliability_buckets(
    claims: list[float], outcomes: list[int], n_buckets: int = 10
) -> list[ReliabilityBucket]:
    """Group claims into equal-width buckets; return per-bucket calibration.

    Reliability calibration measurement (PYRAMID.md Stone 8, FORMULAS.md
    "Calibration measurement"). Bucket `b` covers `[b/B, (b+1)/B)`; the
    last bucket includes 1.0. Each returned `ReliabilityBucket` reports
    `mean_claim` (average claim in the bucket), `observed_rate` (fraction
    of predictions in the bucket whose outcome was 1), and `count`.

    A calibrated agent has `mean_claim ≈ observed_rate` in every bucket.
    Off-diagonal points are diagnostic — `mean_claim > observed_rate` is
    overconfidence; `mean_claim < observed_rate` is underconfidence.

    Empty buckets are omitted. Inputs:
      - `claims`: probabilities in [0, 1]
      - `outcomes`: 0/1, same length as `claims`
      - `n_buckets`: number of equal-width buckets (default 10)
    """
    if len(claims) != len(outcomes):
        raise ValueError(
            f"claims and outcomes must have equal length; got {len(claims)} and {len(outcomes)}"
        )
    if n_buckets < 2:
        raise ValueError(f"n_buckets must be >= 2; got {n_buckets}")

    result: list[ReliabilityBucket] = []
    for b in range(n_buckets):
        lo = b / n_buckets
        hi_open = (b + 1) / n_buckets
        # Last bucket is closed on the right so claim==1.0 still lands.
        is_last = b == n_buckets - 1
        bucket_pairs = [
            (c, o)
            for c, o in zip(claims, outcomes, strict=True)
            if lo <= c < hi_open or (is_last and c == 1.0)
        ]
        if not bucket_pairs:
            continue
        n = len(bucket_pairs)
        mean_claim = sum(c for c, _ in bucket_pairs) / n
        observed_rate = sum(o for _, o in bucket_pairs) / n
        result.append(
            ReliabilityBucket(
                bucket_idx=b,
                lo=lo,
                hi=hi_open,
                mean_claim=mean_claim,
                observed_rate=observed_rate,
                count=n,
            )
        )
    return result
