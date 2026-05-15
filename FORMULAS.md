# Formulas — FinInferenceGym

## Purpose

A reference for the formal symbols, mathematical notation, and core formulas the project uses. Lookup for "what does this symbol mean" and "how is this computed."

Complements [DEFINITIONS.md](DEFINITIONS.md) — DEFINITIONS is the **prose glossary** (concepts, in plain language); FORMULAS is the **symbol and formula reference**. When a term has both, both files have it: DEFINITIONS for the idea, FORMULAS for the notation.

This document grows as new stones are taught. Each entry: the symbol or formula, the plain-language description, the range/type, where it's used in code, and cross-references. Entries are grouped by which stone introduces them.

---

## The four-thing decomposition (Stone 7a)

The vocabulary that distinguishes the four primitives every Layer-2 scoring decision sits inside.

### `S_true`

- **What:** the actual hidden state of the world; the truth reality reveals later.
- **Type:** one value from a fixed enumerable set of hypotheses (e.g., `Literal["strengthening", "stable", "decaying"]`).
- **Visibility:** not known at decision time. Revealed at the horizon.
- **Per-horizon:** the state is defined relative to a time window. `S_true(t+1m)` and `S_true(t+1y)` are different things, scored independently.

### `P_AI(S)`

- **What:** the agent's probability distribution over the state space — its belief.
- **Type:** function from each possible value of `S` to a probability in `[0, 1]`. Values sum to exactly `1`.
- **In code:** `dict[StateLiteral, float]` (see [src/fingym/toys/four_thing_decomp.py](src/fingym/toys/four_thing_decomp.py)). `BeliefDistribution` in [CONTRACT.md](CONTRACT.md).
- **Constraint:** Cromwell's rule (Stone 7) — do not assign probability `0` to anything not logically certain.

### `P_market(S)`

- **What:** the market's belief about the same state space, encoded in observable prices.
- **Type:** distribution of identical shape to `P_AI(S)`.
- **Recovery:** Phase 2 builds implied-DCF, options-implied probabilities, and implied-volatility inversions (Stone 31). Toy worlds in Phase 0 construct `P_market` directly.
- **In code:** `MarketBeliefEstimate` in [CONTRACT.md](CONTRACT.md). `None` is allowed at Phase 0 when no market exists yet (coin toy); required from Phase 2 forward.

### `Action(A)`

- **What:** the agent's chosen action. Determines the payoff distribution.
- **Type:** typed sum: `TradeAction(...) | NoAction`. The two are peers.
- `TradeAction(direction, size, instrument)` — concrete trade with sub-type chosen from Stone 11's expression types (equity-long, option-call, vol-spread, pair, etc.).
- `NoAction` — agent declines to trade. **Not** a `TradeAction` with `size = 0`. A separately typed output, scored separately (Stone 13).

### `belief_delta(S) = P_AI(S) − P_market(S)`

- **What:** the gap between agent and market beliefs, per state.
- **Type:** signed real number per state in the hypothesis space.
- **Identity:** `Σ_h belief_delta(h) = 0` (both distributions sum to `1`, differences cancel). Use as a sanity check.
- **What the evaluator focuses on:** `belief_delta(S_true)` — the gap on the realized truth. Positive = agent correctly more confident than market on the right answer (edge). Zero = no opportunity. Negative = anti-edge (agent monetized in the wrong direction).
- **In code:** `BeliefDelta` field in [CONTRACT.md](CONTRACT.md). Scored by Stone 11a (market-delta scoring).

### Anchor sentence

> Money lives in `belief_delta = P_AI(S) − P_market(S)` only when an `Action(A)` exists whose payoff distribution monetizes that gap after costs, and the realized `S_true` validates the side the agent took.

Four conditions, all required:
1. **Disagreement.** `belief_delta(S_true) ≠ 0`.
2. **Correct.** `belief_delta(S_true) > 0` (agent on the right side, not wrong).
3. **Actionable.** an `Action(A)` exists whose payoff under `S_true` captures the gap.
4. **After costs.** the captured payoff exceeds friction (commissions, spread, slippage, financing, time decay).

If any link fails, no edge.

---

## Proper scoring rules (Stones 6 and 7)

The Layer-1 math primitives. Pure functions of `(P_AI, S_true)`.

### Brier score

```
Brier(P_AI, S_true) = Σ_h (P_AI(h) − 1[h == S_true])²
```

For each hypothesis `h`: take the probability the agent assigned `P_AI(h)`, subtract `1` if `h` is the actual outcome (otherwise subtract `0`), square it, sum across all hypotheses.

- **Range:** `[0, 2]` for any number of hypotheses (binary or multi-class).
- **Min (perfect):** `0.0` when `P_AI(S_true) = 1` and all other probabilities are `0`.
- **Max (catastrophic):** `2.0` when `P_AI(S_true) = 0` and probability `1` is on a single wrong hypothesis.
- **Bounded:** does not blow up on Cromwell violations.
- **Properness proof sketch:** `E_q[Brier(r, y)]` is a quadratic in `r` with `dE/dr = 0` at `r = q`. Reporting the true belief minimizes expected loss.
- **In code:** `src/fingym/evaluator/scoring.py:brier()`.

### Log score

```
log_score(P_AI, S_true) = −ln(P_AI(S_true))
```

Take the probability the agent assigned to the actual outcome; take its natural log; flip the sign so lower = better.

- **Range:** `[0, +∞)`.
- **Min (perfect):** `0.0` when `P_AI(S_true) = 1`.
- **Max:** **unbounded.** `+∞` when `P_AI(S_true) = 0` (Cromwell violation).
- **Cromwell mechanism:** `ln(0) = −∞`, so `−ln(0) = +∞`. The math refuses to forgive ruling out the truth.
- **Properness proof sketch:** `E_q[log_score(r, y)]` has `dE/dr = 0` at `r = q`. Same property as Brier; different shape.
- **In code:** `src/fingym/evaluator/scoring.py:log_score()`.

### The proper property, formally

A scoring rule `S(r, y)` is **proper** if for every true distribution `q`:

```
E_q[S(r, y)] is uniquely minimized at r = q
```

In English: if outcomes follow `q` and the agent reports `r`, expected loss is lowest exactly when `r = q`. **Honest reporting is the dominant strategy** under any proper scoring rule.

The improper counter-example (linear scoring, `S = −belief[outcome]`) has `dE/dr` constant in `r`, so the minimum is at the boundary (`r = 1`). Reward goes to bluffing instead of honesty.

---

## Bayesian update (Stone 1 / intuitions.md #1)

The math of belief revision. Used by the coin toy and any future state-inference agent.

```
P(hypothesis | evidence) = P(evidence | hypothesis) × P(hypothesis) / P(evidence)
```

In our notation:

```
P_AI_new(h) = likelihood(evidence | h) × P_AI_old(h) / Σ_h' [ likelihood(evidence | h') × P_AI_old(h') ]
```

- **Inputs:** prior belief `P_AI_old`, evidence, likelihood model.
- **Output:** posterior belief `P_AI_new`. Distribution; sums to `1`.
- **In code:** `src/fingym/toys/coin.py:update()`.
- **Property:** if prior assigns `0` to a hypothesis, posterior is `0` forever (Cromwell).

---

## Calibration measurement (Stone 8)

Layer-2 measurement of `P_AI` calibration across many predictions. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 8 summary; runnable toy at [src/fingym/toys/calibration_diagram.py](src/fingym/toys/calibration_diagram.py).

### Setup

Given `N` predictions from one agent. For each prediction `i`:

- `q_i` — the agent's stated probability for the positive class (binary case)
- `y_i` — `1` if the positive outcome actually happened, `0` otherwise

### Bucketing

Choose `B` (typically `10`). Divide `[0, 1]` into `B` equal-width intervals. Each prediction's `q_i` falls in exactly one bucket. Let `B_b` denote the set of predictions whose `q_i` falls in bucket `b`.

Convention: bucket `b` covers `[b/B, (b+1)/B)` — lower edge included, upper edge excluded, except the last bucket which includes `1.0`.

### Per-bucket statistics

```
claim(b) = (1 / |B_b|) × Σ_{i ∈ B_b} q_i        # mean claim in the bucket
obs(b)   = (1 / |B_b|) × Σ_{i ∈ B_b} y_i        # observed frequency in the bucket
gap(b)   = | claim(b) − obs(b) |                # absolute discrepancy
```

Calibrated bucket: `claim(b) ≈ obs(b)`. Plotting `(claim(b), obs(b))` per bucket gives the reliability diagram; the line `obs = claim` is perfect calibration.

### Expected Calibration Error (ECE)

```
ECE = (1 / N) × Σ_b |B_b| × gap(b)
```

- Range: `[0, 1]` (or `0–100` percentage points).
- Min (perfect): `0.0` when every bucket has `claim(b) = obs(b)`.
- A weighted average of per-bucket gaps; larger buckets dominate.

### Multi-class extension (top-label calibration)

For multi-class `P_AI`:

```
q_i = max_h P_AI_i(h)                           # confidence on the agent's top guess
y_i = 1 if argmax_h P_AI_i(h) == S_true_i else 0
```

Reduces multi-class to binary; bucket and score as above.

### Important property — calibration is necessary, not sufficient

An uninformative agent (always says `0.5`) can achieve low ECE when the base rate is near `0.5`. ECE alone does not detect this; pair with Brier and log score, which both punish uninformative agents.

The reliability **table** (per-bucket gap structure) is the diagnostic; ECE is the summary. A one-bucket table with low ECE is a red flag — the agent has no discrimination.

### In code

Toy implementation: `src/fingym/toys/calibration_diagram.py`. To be lifted into `src/fingym/evaluator/` as a proper scoreboard component when substep 4b assembles the multi-column evaluator.

---

## How this document grows

Each stone that introduces new formal notation adds an entry here, organized by stone number. Cross-references:

- The **concept** entries (prose, intuitive definitions) live in [DEFINITIONS.md](DEFINITIONS.md).
- The **distilled summary** of each stone's teaching (with formula references back here) lives in [PYRAMID.md](PYRAMID.md).
- The **code implementation** lives in `src/fingym/`.

A formula entry must include: the formula or symbol, plain-language description, range/type, properties relevant to use (boundedness, identities), proof sketch where useful, and a pointer to the implementation. Future entries follow this pattern.

### Upcoming entries (parked, to be filled in as taught)

- Scoreboard aggregation operators (Stone 9)
- Multi-horizon scoring composition (Stone 10)
- Expression-type payoff structures (Stone 11)
- Market-delta scoring formula (Stone 11a)
- Process-quality metric (Stone 12)
- Decision-quality with NoAction first-class (Stone 13)
- Capacity-adjusted return: `edge_realized = nominal_edge − market_impact(size)` (Stone 14)
- Implied DCF (Stone 31)
- Options-implied probabilities (Stone 31)
- Kelly fraction: `f* = edge / odds_squared` (Stone 33)
- Fractional Kelly: `f_practical = k · f*` where `k ∈ [0.25, 0.5]` (Stone 33)
- Asymmetry of ruin: `recover_gain_required = drawdown / (1 − drawdown)` (intuitions.md #12)
