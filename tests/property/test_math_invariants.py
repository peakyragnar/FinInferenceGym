"""Stone 21 — property tests for the math primitives (Phase 0 substep 8).

Hypothesis-based property tests covering the architectural-physics
functions: Bayesian update, Brier and log_score scoring rules, and the
Stone 11a market-delta scoring. These are the "physics" of the verifier
(DESIGN.md "Architectural Physics" + #5 cognition/verification boundary;
"the verifier may encode physics, not alpha"). Properties tested here
should hold mechanically — if any fail, the verifier is broken.

Properties tested (one or more per primitive):

  Bayesian update — coin and synthetic-market 3-state believer:
    - Commutativity: update(update(p, A), B) == update(update(p, B), A)
      for any pair of independent emissions A, B. Standard Bayes
      property; if it fails, the update math is wrong.

  Brier score (multi-class, generic over hypothesis alphabet):
    - Properness in expectation: for any true distribution q and any
      reported distribution r, E_y~q[Brier(q, y)] <= E_y~q[Brier(r, y)].
      Reporting the truth minimizes expected loss; lying costs more.

  Log score (multi-class):
    - Properness in expectation: same property, different metric.

  belief_delta_on_truth (Stone 11a):
    - Signed inverse: gap(P_AI, P_market, t) == -gap(P_market, P_AI, t).
    - Sum across states: sum of belief_delta across all states is zero
      (because both distributions sum to 1).

  reliability_buckets (Stone 8 / Stone 18):
    - Count invariant: the sum of `count` over all returned buckets
      equals the number of input claim/outcome pairs.

The smoke subset is the Phase 0 substep 8 deliverable. If any test
fails, Phase 0 cannot exit.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from fingym.evaluator.scoring import (
    ReliabilityBucket,
    belief_delta_on_truth,
    brier,
    log_score,
    reliability_buckets,
)
from fingym.toys.coin import Coin, Flip
from fingym.toys.coin import update as coin_update
from fingym.toys.synthetic_market import (
    STATES,
    CompanyState,
    Emission,
)
from fingym.toys.synthetic_market import update as sm_update

# ---------------------------------------------------------------------------
# Strategies — sample valid belief distributions and emissions.
# ---------------------------------------------------------------------------

_GENERIC_STATES = ("a", "b", "c")


@st.composite
def coin_belief(draw: st.DrawFn) -> dict[Coin, float]:
    """Sample a valid Coin belief. Min prob 0.01 to avoid Cromwell."""
    p_fair = draw(st.floats(min_value=0.01, max_value=0.99))
    return {"fair": p_fair, "biased": 1.0 - p_fair}


@st.composite
def sm_belief(draw: st.DrawFn) -> dict[CompanyState, float]:
    """Sample a valid 3-state synthetic-market belief (Cromwell-respecting)."""
    raw = [draw(st.floats(min_value=0.01, max_value=1.0)) for _ in range(3)]
    total = sum(raw)
    assume(total > 1e-6)
    return {state: r / total for state, r in zip(STATES, raw, strict=True)}


@st.composite
def generic_belief_3state(draw: st.DrawFn, min_prob: float = 0.0) -> dict[str, float]:
    """Sample a generic 3-state belief over the alphabet ('a', 'b', 'c').

    Cromwell allowed iff min_prob == 0; otherwise each prob is at least
    min_prob before normalization.
    """
    raw = [draw(st.floats(min_value=min_prob, max_value=1.0)) for _ in range(3)]
    total = sum(raw)
    assume(total > 1e-6)
    return {state: r / total for state, r in zip(_GENERIC_STATES, raw, strict=True)}


flip_strategy = st.sampled_from(("heads", "tails"))
emission_strategy = st.sampled_from(("strong", "mixed", "weak"))
generic_outcome = st.sampled_from(_GENERIC_STATES)


# ---------------------------------------------------------------------------
# Bayesian update — commutativity.
# ---------------------------------------------------------------------------


@given(prior=coin_belief(), flip1=flip_strategy, flip2=flip_strategy)
def test_coin_update_is_commutative(prior: dict[Coin, float], flip1: Flip, flip2: Flip) -> None:
    """update(update(p, A), B) == update(update(p, B), A) for coin.

    Two independent observations can be incorporated in either order
    without changing the posterior. Standard Bayes property.
    """
    a_then_b = coin_update(coin_update(prior, flip1), flip2)
    b_then_a = coin_update(coin_update(prior, flip2), flip1)
    for coin in ("fair", "biased"):
        assert math.isclose(a_then_b[coin], b_then_a[coin], abs_tol=1e-9), (
            f"Coin Bayes commutativity violated for {coin}: {a_then_b[coin]} != {b_then_a[coin]}"
        )


@given(
    prior=sm_belief(),
    emission1=emission_strategy,
    emission2=emission_strategy,
)
def test_synthetic_market_update_is_commutative(
    prior: dict[CompanyState, float],
    emission1: Emission,
    emission2: Emission,
) -> None:
    """update(update(p, A), B) == update(update(p, B), A) for 3-state toy."""
    a_then_b = sm_update(sm_update(prior, emission1), emission2)
    b_then_a = sm_update(sm_update(prior, emission2), emission1)
    for state in STATES:
        assert math.isclose(a_then_b[state], b_then_a[state], abs_tol=1e-9), (
            f"SM Bayes commutativity violated for {state}: {a_then_b[state]} != {b_then_a[state]}"
        )


# ---------------------------------------------------------------------------
# Brier score — properness in expectation.
# ---------------------------------------------------------------------------


@given(q=generic_belief_3state(), r=generic_belief_3state())
def test_brier_is_proper_in_expectation(q: dict[str, float], r: dict[str, float]) -> None:
    """E_y~q[Brier(q, y)] <= E_y~q[Brier(r, y)] for any q, r.

    A proper scoring rule has the property that, given a true outcome
    distribution q, reporting q (the truth) minimizes expected score.
    Reporting anything else (r != q) is at least as bad. This is the
    formal statement of why proper scoring rules incentivize honesty.
    """
    e_brier_q = sum(q[s] * brier(q, s) for s in _GENERIC_STATES)
    e_brier_r = sum(q[s] * brier(r, s) for s in _GENERIC_STATES)
    # Tolerance handles tiny floating-point noise around the boundary.
    assert e_brier_q <= e_brier_r + 1e-9, (
        f"Brier properness violated: E[Brier(q)]={e_brier_q} > E[Brier(r)]={e_brier_r} + tol"
    )


# ---------------------------------------------------------------------------
# Log score — properness in expectation.
# ---------------------------------------------------------------------------


@given(
    q=generic_belief_3state(min_prob=0.01),
    r=generic_belief_3state(min_prob=0.01),
)
def test_log_score_is_proper_in_expectation(q: dict[str, float], r: dict[str, float]) -> None:
    """E_y~q[log_score(q, y)] <= E_y~q[log_score(r, y)] for any q, r.

    Same property as Brier; different metric. min_prob=0.01 keeps
    log_score finite (no Cromwell violations in this expectation
    calculation).
    """
    e_log_q = sum(q[s] * log_score(q, s) for s in _GENERIC_STATES)
    e_log_r = sum(q[s] * log_score(r, s) for s in _GENERIC_STATES)
    assert e_log_q <= e_log_r + 1e-9, (
        f"Log_score properness violated: E[log(q)]={e_log_q} > E[log(r)]={e_log_r} + tol"
    )


# ---------------------------------------------------------------------------
# belief_delta_on_truth — signed inverse and sum-to-zero.
# ---------------------------------------------------------------------------


@given(
    p_ai=generic_belief_3state(),
    p_market=generic_belief_3state(),
    truth=generic_outcome,
)
def test_belief_delta_is_signed_inverse(
    p_ai: dict[str, float],
    p_market: dict[str, float],
    truth: str,
) -> None:
    """gap(P_AI, P_market, t) == -gap(P_market, P_AI, t).

    The gap is the signed difference P_AI(t) - P_market(t). Swapping
    the arguments must negate the sign.
    """
    forward = belief_delta_on_truth(p_ai, p_market, truth)
    reverse = belief_delta_on_truth(p_market, p_ai, truth)
    assert math.isclose(forward, -reverse, abs_tol=1e-9), (
        f"belief_delta signed-inverse violated: forward={forward}, reverse={reverse}"
    )


@given(
    p_ai=generic_belief_3state(),
    p_market=generic_belief_3state(),
)
def test_belief_delta_across_states_sums_to_zero(
    p_ai: dict[str, float],
    p_market: dict[str, float],
) -> None:
    """sum_s gap(P_AI, P_market, s) == 0 across all states in the support.

    Both belief distributions sum to 1, so their per-state differences
    must sum to 0. This is the algebraic identity behind "agent's extra
    probability on one state is matched by less probability on others"
    (see Stone 11a teaching).
    """
    total = sum(belief_delta_on_truth(p_ai, p_market, s) for s in _GENERIC_STATES)
    assert math.isclose(total, 0.0, abs_tol=1e-9), f"belief_delta cross-state sum != 0: {total}"


# ---------------------------------------------------------------------------
# reliability_buckets — count invariant.
# ---------------------------------------------------------------------------


@given(
    pairs=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            st.integers(min_value=0, max_value=1),
        ),
        min_size=1,
        max_size=200,
    ),
    n_buckets=st.integers(min_value=2, max_value=20),
)
def test_reliability_buckets_count_invariant(
    pairs: list[tuple[float, int]], n_buckets: int
) -> None:
    """sum(bucket.count) over all returned buckets == len(input).

    The bucketer partitions the input into buckets; empty buckets are
    omitted. The total count across non-empty buckets must recover the
    input size.
    """
    claims = [c for c, _ in pairs]
    outcomes = [o for _, o in pairs]
    buckets: list[ReliabilityBucket] = reliability_buckets(claims, outcomes, n_buckets=n_buckets)
    total_count = sum(b.count for b in buckets)
    assert total_count == len(claims), (
        f"Reliability bucket count invariant violated: sum={total_count}, expected={len(claims)}"
    )


# ---------------------------------------------------------------------------
# A focused regression check — Brier minimum on a degenerate truth belief.
# ---------------------------------------------------------------------------


@given(truth=generic_outcome)
def test_brier_is_zero_on_degenerate_correct_belief(truth: str) -> None:
    """A belief that places probability 1 on the truth scores Brier = 0.

    The minimum-possible Brier is 0; achieved when the agent's belief
    exactly matches the realized outcome with full mass.
    """
    belief = {s: (1.0 if s == truth else 0.0) for s in _GENERIC_STATES}
    score = brier(belief, truth)
    assert score == pytest.approx(0.0, abs=1e-12)
