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

## Scoreboard schema (Stone 9)

The Layer-2 data structure that holds evaluation results. Each row corresponds to one `Contract` (see [CONTRACT.md](CONTRACT.md)).

### Row schema (grows column-by-column per stone)

```
Scoreboard row {
  # Identity and metadata (for slicing)
  prediction_id:    UUID
  decision_time:    datetime
  agent_id:         str
  model_id:         str
  prompt_version:   str
  horizon:          str            # "1m", "3m", "6m", "1y", ...
  expression_type:  str            # "equity-long" / "option-call" / "no-action" / ...
  sector:           str | None

  # What the agent emitted
  agent_claim:      BeliefDistribution   # P_AI(S)

  # What reality delivered (filled in at horizon)
  outcome:          HypothesisLabel      # S_true
  outcome_positive: bool                 # for binary calibration

  # Scoring columns (filled in by evaluator; grow per stone)
  brier:                 float
  log_score:             float            # may be +inf (Cromwell)
  claim_bucket:          int              # 0..9, for ECE aggregation

  # Future columns (placeholders, populated as stones land)
  # belief_delta_on_truth: float           # Stone 11a
  # process_quality_flag:  bool            # Stone 12
  # decision_quality:      float           # Stone 13
  # capacity_adjusted:     float           # Stone 14
}
```

### Operations

- **Aggregate per column.** `mean(scoreboard.brier)`, `mean(scoreboard.log_score where not cromwell)`, etc.
- **Slice by metadata.** `scoreboard.filter(horizon=="6m").mean(brier)`, etc.
- **Compare agents.** Same scoreboard with `agent_id` column lets aggregations group by agent.
- **Collapse to scalar.** Only at decision points; rule must be declared and written down.

### Implementation

- Schema: `src/fingym/evaluator/scoreboard.py` (Phase 0 substep 4b/4c deliverable).
- Storage: Postgres table per the data spine (L0 trajectory records, see [memory-design.md](memory-design.md)).
- Immutable, append-only. Aggregations computed from the immutable rows; no row updated in place.

### Connection to other stones

- Brier (Stone 6) — populates `brier` column.
- log_score (Stone 7) — populates `log_score` column.
- Calibration (Stone 8) — uses `claim_bucket` for aggregation; produces ECE per agent.
- Stones 10–14 — each adds its column.

---

## Multi-horizon scoring (Stone 10)

State is per-horizon by default. A single decision-time produces multiple `Contract` rows, one per horizon the agent cares about. The scoreboard's `horizon` column distinguishes them; per-horizon aggregations and per-horizon promotion gates fall out of slicing by that column.

### Setup

- `horizons: list[Horizon]` — configurable per evaluator run. Standard: `["1m", "3m", "6m", "1y"]`. Toys may use shorter (days or flips).
- For each decision-time `t` and each horizon `h`, the agent emits one Contract.
- `S_true(t, h)` — the truth as of time `t + h`. Distinct per horizon; revealed at horizon.

### Per-horizon scoring

Each Contract's evaluation columns (Brier, log_score, claim_bucket, etc.) are computed against `S_true(t, h)` — the truth at *that horizon*, not at the decision time.

### Per-horizon aggregations

```
mean_brier_at_horizon(h)        = mean(scoreboard[horizon==h].brier)
mean_log_score_at_horizon(h)    = mean(scoreboard[horizon==h].log_score where not cromwell)
ece_at_horizon(h)               = ECE computed using only rows where horizon == h
```

### Per-horizon promotion gate

The four-check promotion gate runs independently per horizon. A skill is promoted with a domain-of-validity `horizon` list containing exactly those horizons where all four checks passed:

```
candidate_skill.domain_of_validity.horizons = [
    h for h in horizons
    if held_out_calibration_improves(h)
    and cross_model_regression_passes(h)
    and survivorship_check_passes(h)
]
```

At inference time, the agent operating at horizon `h_decision` only sees skills whose `domain_of_validity.horizons` includes `h_decision`.

### In code

- Contract carries `horizon: str` (see [CONTRACT.md](CONTRACT.md)).
- Scoreboard row carries `horizon: str` column (see Stone 9 schema above).
- Domain-of-validity in memory artifact carries `horizons: list[str]` (see [memory-design.md](memory-design.md)).

The three structures align — a Contract's horizon is the row's horizon is the skill's authorized horizon.

---

## Expression-type tagging within `TradeAction` (Stone 11)

Same belief, different expressions = different payoff structures. The scoreboard's `expression_type` column is the **broad category** for slicing; full trade details live inside the `TradeAction` object on the Contract.

### The expression-type categories

```
ExpressionType = Literal[
  "equity-long",       "equity-short",
  "option-call",       "option-put",
  "option-spread",     "option-straddle",  "option-strangle",
  "vol-long",          "vol-short",
  "pair",              # / relative-value
]
```

### Distinction: category vs full spec

The scoreboard column captures only the category (`expression_type`). Full trade details (underlying, direction, strike, expiration, premium, size) live inside the `TradeAction` object:

```
TradeAction {
  expression_type:  ExpressionType   # ← scoreboard column
  underlying:       str              # e.g., "AAPL"
  direction:        Literal["long", "short"]
  strike:           float | None     # for options
  expiration:       date | None      # for options
  premium_per_unit: float | None     # for options
  size:             int              # shares or contracts
  notional:         float            # USD exposure
}
```

The category is for slicing (statistical power). The full spec is for payoff math (Stones 13 and 14).

### Per-expression-type promotion gate

Same logic as per-horizon (Stone 10). A candidate skill carries `expression_type: list[ExpressionType]` in its domain-of-validity, containing only the expression types where all four promotion checks passed.

At inference time, the agent's action choice is filtered to skills whose `domain_of_validity.expression_types` includes the agent's chosen expression.

### Stacking with other slicing dimensions

A skill's domain-of-validity is multi-dimensional:

```
domain_of_validity {
  horizons:         list[Horizon]
  expression_types: list[ExpressionType]
  sectors:          list[Sector]
}
```

A skill might apply ONLY at `horizons=[3m, 6m] ∩ expression_types=[equity-long] ∩ sectors=[tech_hardware]`. Narrowly tagged, narrowly applied. Each slicing dimension is independent.

### `NoAction` is a peer, not a sub-type

```
ActionOrNoAction = TradeAction | NoAction

NoAction { decision_time: datetime, reason: str }
```

`NoAction` has no payoff structure to evaluate. Scored separately by Stone 13 — was the gap correctly below the cost threshold? Different scoring path from any `TradeAction`.

### In code

- `expression_type` field on scoreboard row.
- `TradeAction` typed in `src/fingym/agents/contract.py` (Phase 0 substep 6 deliverable).
- Per-expression-type aggregations: `scoreboard.filter(expression_type==X).mean(...)`.

---

## How this document grows

Each stone that introduces new formal notation adds an entry here, organized by stone number. Cross-references:

- The **concept** entries (prose, intuitive definitions) live in [DEFINITIONS.md](DEFINITIONS.md).
- The **distilled summary** of each stone's teaching (with formula references back here) lives in [PYRAMID.md](PYRAMID.md).
- The **code implementation** lives in `src/fingym/`.

A formula entry must include: the formula or symbol, plain-language description, range/type, properties relevant to use (boundedness, identities), proof sketch where useful, and a pointer to the implementation. Future entries follow this pattern.

### Upcoming entries (parked, to be filled in as taught)

- Market-delta scoring formula (Stone 11a)
- Process-quality metric (Stone 12)
- Decision-quality with NoAction first-class (Stone 13)
- Capacity-adjusted return: `edge_realized = nominal_edge − market_impact(size)` (Stone 14)
- Implied DCF (Stone 31)
- Options-implied probabilities (Stone 31)
- Kelly fraction: `f* = edge / odds_squared` (Stone 33)
- Fractional Kelly: `f_practical = k · f*` where `k ∈ [0.25, 0.5]` (Stone 33)
- Asymmetry of ruin: `recover_gain_required = drawdown / (1 − drawdown)` (intuitions.md #12)
