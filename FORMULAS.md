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
- **In code:** `dict[StateLiteral, float]`; `BeliefDistribution` in [CONTRACT.md](CONTRACT.md).
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

Layer-2 measurement of `P_AI` calibration across many predictions. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 8 summary.

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

Production implementation lands in `src/fingym/evaluator/` as a proper scoreboard component when substep 4b assembles the multi-column evaluator.

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

## Market-delta scoring (Stone 11a)

The first scoreboard column that takes `P_market` into the math. Operationalizes the four-thing decomposition's monetization layer. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 11a body.

### Per-row formula

```
belief_delta_on_truth = P_AI(S_true) - P_market(S_true)
```

- **Inputs:** the agent's belief, the market's belief, the revealed truth.
- **Range:** `[-1, +1]`.
- **Sign convention:**
  - `> 0` — agent more confident on truth than market (edge)
  - `= 0` — agreement (no edge to extract)
  - `< 0` — agent less confident on truth than market (anti-edge)

### Aggregation

```
mean_gap_on_truth = mean over all scoreboard rows of belief_delta_on_truth
```

Aggregations follow Stone 9's scoreboard discipline — can be sliced by `horizon`, `expression_type`, `sector`, `agent_id`, etc.

### Sliceable comparisons

```
mean_gap_at_horizon(h)        = mean(rows where horizon==h).belief_delta_on_truth
mean_gap_for_expression(e)    = mean(rows where expression_type==e).belief_delta_on_truth
```

Tells you where (which horizon, which expression-type) the agent's edge actually lives.

### Independence from Layer 1

`belief_delta_on_truth` is structurally independent of Brier and log_score:

- Brier and log_score use only `(P_AI, S_true)`. They don't see `P_market`.
- `belief_delta_on_truth` uses `(P_AI, P_market, S_true)`. It alone sees the market.

Same `(P_AI, S_true)` → identical Brier and log_score; varying `P_market` → varying `belief_delta_on_truth`. The toy demonstrates this.

### Used by the promotion gate

A candidate skill at promotion time is checked for whether it improves the mean `belief_delta_on_truth` on held-out data — not just whether it improves Brier. A skill that produces better-calibrated beliefs that happen to agree with the market doesn't produce edge.

### `P_market` source

- **Phase 0 (toys):** `P_market` constructed directly by the test scaffold.
- **Phase 2 (real markets):** `P_market` recovered from observable prices via the inversion mechanism (Stone 31 — implied DCF, options-implied probabilities, implied volatility). Recovery is approximate; the structural gap is still surfaced.

### Connection forward

- Stone 13 (decision-quality): uses `belief_delta` plus the chosen `Action(A)` to score whether the action sensibly captures the gap.
- Stone 14 (capacity-adjusted return): uses `belief_delta` plus market-impact model to score whether the gap survives at deployable size.

### In code

- `belief_delta` field on each Contract (see [CONTRACT.md](CONTRACT.md), Phase 0 substep 6 deliverable).
- `belief_delta_on_truth` column on scoreboard row (Stone 9 schema, populated at horizon when `S_true` is revealed).

---

## Process-quality flag (Stone 12, narrow form)

A single mechanical check fired at update time: did an emission exist in the window before this belief update? Tags each update as `motivated` or `unmotivated`. Aggregated to an `unmotivated_update_rate` per agent and capped at promotion. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 12 body.

### Scope (deliberately narrow)

Stone 12 does NOT inspect reasoning-trace content to judge whether the agent used the emission's content vs the market's reaction. That distinction collapses in reality — price IS the market's instant update on the same emission, so the two are not independent signals. The output-side scoring (Brier, log_score, `belief_delta_on_truth`) handles that judgment after the horizon closes. Stone 12 only asks the question that has a clean mechanical answer at update time.

### Per-update tagging

For each belief update `u` emitted by an agent (each Contract whose belief differs from the prior Contract's belief on the same underlying):

```
emission_in_window(u) = ∃ emission e :
                        e.as_known ∈ (prior_update.decision_time, u.decision_time]
                        AND e.underlying == u.underlying

motivated_flag(u) = "motivated"   if emission_in_window(u)
                    "unmotivated" otherwise
```

The check is a database query. No reasoning-trace inspection. No model-based classification.

### Per-agent aggregation

```
unmotivated_update_rate(agent) =
    |{u : motivated_flag(u) = "unmotivated"}| / |all updates by agent|
```

- **Range:** `[0, 1]`.
- **Interpretation:** fraction of updates the agent emitted with no new emission in the world to react to.
- **Threshold (initial):** `0.10`. Agents above this cannot be promoted regardless of Layer-1 / Layer-2 output scores.

### Sliced aggregations

```
unmotivated_rate_at_horizon(agent, h)     = restrict to rows where horizon == h
unmotivated_rate_for_expression(agent, e) = restrict to rows where expression_type == e
unmotivated_rate_in_sector(agent, s)      = restrict to rows where sector == s
```

A skill might be motivated at `equity-long` (updates only on filings) and unmotivated at `vol-spread` (updates on VIX chart patterns). Promotion gate evaluates per-slice.

### Connection to other stones — the two-face defense

The price-tracking failure mode has two faces, caught by different stones:

| Face | Mechanism | Caught by |
|---|---|---|
| Pure tape-reader | Updates fire with no emission in window | Stone 12 (this check, at update time) |
| Sophisticated tape-reader | Waits for emission, then mirrors market | Stone 11a (`belief_delta_on_truth ≈ 0` at horizon) |

Stone 12 is fast and binary; Stone 11a is slow and continuous. Together they bracket the failure mode without requiring reasoning-trace inspection or ablation.

### Scoreboard row addition

Adds to Stone 9 schema:

```
emission_in_window:  bool
motivated_flag:      Literal["motivated", "unmotivated"]
emission_ids:        list[UUID]   # emission rows in the pre-update window, if any
```

`emission_ids` is stored for downstream forensics (which disclosures preceded the update) but is NOT interpreted by Stone 12. Subsequent analyses (Stone 13 decision-quality, retrospective audits) may join on emission_ids.

### Implementation note

The tagger is a deterministic SQL/code-level check against the emissions table — no model, no NLP, no classifier. Lives in `src/fingym/evaluator/`, not in `src/fingym/agents/` — process-quality is verification, not cognition (DESIGN.md #5).

### What this metric does NOT measure

- Whether the agent's reasoning is logically sound.
- Whether the agent cited the emission's content or the price reaction (deliberately rejected — see Scope above).
- Whether the cited evidence is true or fabricated.
- Whether the update was the *right* update given the available evidence (Layer-1 scoring on the resulting belief handles that).

It measures only: did the agent issue an update with no new emission in the world to react to?

### Why this is enough

- Pure tape-readers are caught directly.
- Sophisticated price-mirroring agents are caught by Stone 11a's market-delta scoring.
- The common case (emission and price moving together) is correctly classified as `motivated` and not penalized — preserving statistical power on the cases that matter.
- The check is deterministic, cheap, fires at update time, and has no false-flag failure mode against legitimate agents.

---

## Decision-quality with NoAction as first-class peer (Stone 13)

Per-Contract coherence check on the agent's action against the inputs (belief, gap, costs) at decision time. Three independent sub-checks; if all pass, the action is coherent. `decision_quality_rate` is a scoreboard COLUMN (not a hard cap) — the promotion gate combines it with other signals. Sub-flags are stored independently so the gate can diagnose what failed. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 13 body.

### The three coherence predicates

For each Contract `c` with belief `P_AI`, market belief `P_market`, gap `belief_delta(S) = P_AI(S) − P_market(S)`, cost threshold `cost`, and action `A`:

**Threshold match.**
```
threshold_match(c) = True iff
    (A is TradeAction AND max_S |belief_delta(S)| > cost)
 OR (A is NoAction    AND max_S |belief_delta(S)| ≤ cost)
```

**Direction match.** Defined only when `A is TradeAction`:
```
direction_match(c) = True iff
    payoff_side(A) aligns with sign of belief_delta(S*)
    where S* = argmax_S |belief_delta(S)|
```

`payoff_side` mapping:
- `equity-long` ↔ positive gap on bullish state
- `equity-short` ↔ positive gap on bearish state
- `option-call` ↔ positive gap on bullish state above strike
- `option-put` ↔ positive gap on bearish state below strike
- etc.

For `NoAction`: trivially True (no direction to check).

**Expression match.** Defined only when `A is TradeAction`. Belief shape categories:
```
shape(P_AI) = "directional"        if max_S P_AI(S) > 0.5 AND argmax is single
              "bimodal"            if two states tied within 5pp AND middle is < 20%
              "uncertain-flat"     if max_S P_AI(S) < 0.45 (no concentration)
              "uncertain-peaked"   if max_S P_AI(S) ∈ [0.45, 0.55]
```

```
expression_match(c) = True iff expression_type(A) is in
                      compatible_expressions(shape(P_AI))
```

Where `compatible_expressions`:
- `directional` → `{equity-long, equity-short, option-call, option-put}` (depending on side)
- `bimodal` → `{option-straddle, option-strangle, vol-long}`
- `uncertain-flat` → `{NoAction}` (no edge; should not trade)
- `uncertain-peaked` → `{vol-long, option-straddle}` (bet on resolution)

For `NoAction`: trivially True.

### Verdict

```
coherent(c) = threshold_match(c) AND direction_match(c) AND expression_match(c)
```

Sub-flag fields on the scoreboard row (stored independently):
```
threshold_miss:  bool   # True if threshold_match failed
direction_miss:  bool   # True if direction_match failed
expression_miss: bool   # True if expression_match failed
coherent_flag:   bool   # True iff all three above are False
```

### Per-agent aggregation

```
decision_quality_rate(agent) =
    |{c : coherent(c)}| / |Contracts by agent|
```

- **Range:** `[0, 1]`.
- **Interpretation:** fraction of Contracts where the action passed all three coherence checks.
- **NOT a hard cap.** Stone 13's rate is a scoreboard column. The promotion gate combines it with `belief_delta`, `unmotivated_update_rate`, held-out replay return, Kelly-sizing quality, etc., using an explicit collapse rule per [PYRAMID.md](PYRAMID.md) Stone 9. A modest `decision_quality_rate` can be redeemed by strong values on other columns (sophisticated agents legitimately deviate from textbook coherence for crowding, hedging, vol-pricing reasons the three checks don't model).

### Per-sub-flag aggregations

```
threshold_miss_rate(agent)  = |{c : threshold_miss(c)}|  / |Contracts|
direction_miss_rate(agent)  = |{c : direction_miss(c)}|  / |Contracts where TradeAction|
expression_miss_rate(agent) = |{c : expression_miss(c)}| / |Contracts where TradeAction|
```

Diagnostic shapes the promotion gate looks for:

- **High threshold-miss rate** → trade-for-trade's-sake agent (trades below cost constantly). Maps to BIAS_PATTERNS #12.
- **High direction-miss rate** → belief and action disagree on which side to take. Possible sign-error in cognition.
- **High expression-miss rate** → reads belief shape but picks wrong instrument. Model hasn't internalized payoff structures.

### Sliced aggregations

```
decision_quality_at_horizon(agent, h)        = restrict to rows where horizon == h
decision_quality_for_expression(agent, e)    = restrict to rows where expression_type == e
decision_quality_in_sector(agent, s)         = restrict to rows where sector == s
```

A skill might be coherent at `equity-long` but incoherent at `vol-long`. Per-slice promotion gate evaluates accordingly.

### Connection to other stones

- **Stone 11a (`belief_delta_on_truth`).** Stone 13 alone cannot distinguish a lazy `NoAction`-always agent from a discriminating one — both score similarly on coherence rate. Stone 11a's near-zero mean gap on the lazy agent unmasks them. The two columns together do what neither does alone.
- **Stone 12 (`unmotivated_update_rate`).** Hard-capped at 0.10; Stone 13 is NOT. The difference: Stone 12 has no compensating virtue (price-following is always wrong), so a hard cap is justified. Stone 13 has compensating virtue (legitimate deviations exist), so column-with-rules is the right shape.
- **Stone 33 (Kelly sizing).** Sizing is deliberately out of Stone 13. Stone 13 scores the discrete decision (trade/not, direction, expression); Stone 33 scores the size.
- **Stone 14 (capacity-adjusted return).** Capacity is also out of Stone 13. A coherent decision that's too big to deploy at scale is still coherent in Stone 13's sense; Stone 14 catches the scale problem.

### What Stone 13 does NOT measure

- Sizing (Stone 33).
- Capacity (Stone 14).
- Whether the trade made money (rejected — DESIGN.md #1, Stone 4). Outcome-grading is not Stone 13's job; a coherent decision can lose, an incoherent decision can win.
- Whether the agent's belief is well-calibrated (Stones 6–8 handle that).
- Whether the agent's gap is structural edge (Stone 11a).

Stone 13 only asks: given everything the agent knew at decision time, was the action a rational response?

### Scoreboard row additions

Adds to Stone 9 schema:

```
threshold_miss:    bool
direction_miss:    bool
expression_miss:   bool
coherent_flag:     bool          # derived: NOT (any of above)
cost_threshold:    float         # the cost used in threshold_match
gap_on_argmax:     float         # max_S |belief_delta(S)|, the value compared to cost
S_star:            HypothesisLabel  # argmax_S |belief_delta(S)|
```

### Implementation note

Pure-function checks on Contract fields. No model, no NLP, deterministic. Lives in `src/fingym/evaluator/`. Cost model is a separate component referenced by `cost_threshold` (initially a placeholder; refined in Phase 2 when real cost models land).

`NoAction` is a typed peer of `TradeAction` per [CONTRACT.md](CONTRACT.md); Stone 13 does NOT score it as `size = 0`. `NoAction` Contracts pass coherence iff their threshold-match passes (the gap was below cost); direction-match and expression-match are trivially True.

---

## Capacity-adjusted return (Stone 14)

Per-Contract realized edge after frictions. Closes the loop between nominal edge (the gap as measured by Stone 11a) and what survives in the account at the agent's stated size. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 14 body.

### Per-Contract formula

```
realized_edge(c) = nominal_edge(c)
                 - spread_cost(c)
                 - commission(c)
                 - impact_cost(c)
                 - alpha_decay_cost(c)
```

Where:

- `nominal_edge(c)` — the gap on the truth-candidate state from Stone 11a, expressed in payoff terms (the gap times the payoff-per-unit-probability for the chosen expression).
- `spread_cost(c) = round_trip_spread(underlying) × notional(size)` — half-spread on each leg.
- `commission(c)` — fixed per trade (often zero at retail).
- `impact_cost(c)` — modeled by the square-root law below.
- `alpha_decay_cost(c)` — modeled per execution horizon.

### Square-root market impact

Standard empirical model (Almgren et al.):

```
impact_cost(c) = k × σ(underlying) × sqrt(size(c) / ADV(underlying)) × notional(c)
```

Where:

- `k` — calibration constant (typically `0.5–1.0`; empirical, varies by venue and asset class).
- `σ(underlying)` — daily volatility of the underlying.
- `ADV(underlying)` — average daily volume in dollars.
- `size(c)` — the agent's stated trade size in dollars.
- `notional(c)` — the dollar exposure (often same as `size(c)`).

The square-root scaling means: 10× the size → ~3× the impact cost (not 10×). Impact dominates spread for large size; spread dominates impact for small size.

### Alpha decay during execution

```
alpha_decay_cost(c) = nominal_edge(c) × decay_factor(execution_days)
```

Where `decay_factor` grows with the execution horizon (a position spread over 5 days suffers more decay than one filled in a single print). Calibration is empirical from execution data; at Phase 0, a simple linear model suffices.

### Per-agent aggregations

```
mean_realized_edge(agent)        = mean(realized_edge across Contracts)
mean_nominal_edge(agent)         = mean(nominal_edge across Contracts)
realized_to_nominal_ratio(agent) = mean_realized_edge(agent) / mean_nominal_edge(agent)
```

- **`mean_realized_edge`**: range unbounded (can be negative). Sign of mean realized edge is the most basic test — must be `> 0` for any agent claiming to have edge.
- **`realized_to_nominal_ratio`**: typically in `[0, 1]` for working agents; below `0` if the strategy structurally loses to friction; close to `1` for capacity-friendly strategies at small size.

### Sliced aggregations — size buckets are the primary slicing dimension

```
mean_realized_edge_at_size(agent, size_bucket) =
    mean(realized_edge across Contracts where notional ∈ size_bucket)
```

Standard size buckets: `[$1K-$10K, $10K-$100K, $100K-$1M, $1M-$10M, $10M-$100M, $100M+]`. The capacity profile across these buckets reveals where each agent's edge actually lives.

Additional slicing dimensions:

```
mean_realized_edge_for_expression(agent, e)   = restrict to expression_type == e
mean_realized_edge_in_sector(agent, s)        = restrict to sector == s
mean_realized_edge_at_horizon(agent, h)       = restrict to horizon == h
```

### Promotion-gate role

- **Column, NOT a hard cap on the aggregate.** A high-aggregate-realized-edge agent at $10K may be loss-making at $100M; the gate evaluates the full size profile.
- **One near-tautological structural check.** `mean_realized_edge` at the agent's stated deployable-size range must be `> 0`. This is what "having an edge" means; below zero is not a calibrated threshold but a definition. Different from Stone 13's column treatment, this is a genuine gate — there is no compensating virtue for "loses money at the size I want to deploy."
- **Per-slice tagging.** Skill that passes at `equity-long mega-cap @ $1M-$10M` may not pass at `equity-long microcap @ $1M-$10M`. The `domain_of_validity` for a promoted skill carries the size-bucket × expression-type × sector slices where realized edge passed.

### Scoreboard row additions

Adds to Stone 9 schema:

```
nominal_edge:        float       # from Stone 11a, in payoff terms
spread_cost:         float
commission:          float
impact_cost:         float
alpha_decay_cost:    float
realized_edge:       float       # nominal_edge minus all four costs
size_bucket:         str         # bucket label for slicing
realized_to_nominal: float       # per-Contract ratio
```

### Cost-model dependency

Stone 14's accuracy depends on the cost model. Phase 0 (toys) uses constructed simple models:

- Fixed spread per name from a stub mapping.
- `k = 0.5`, square-root impact.
- Linear alpha decay over execution_days.

Phase 2+ refines from observed execution data. The deferred-fields list in [CONTRACT.md](CONTRACT.md) (`cost_model`, `slippage_model`, `capacity_estimate`, `payoff_distribution`) maps onto Stone 14's inputs. Their arrival is what makes Stone 14 production-quality rather than toy-quality.

### Connection to other stones

- **Stone 11a (`belief_delta_on_truth`).** Stone 14 takes `nominal_edge` as input; Stone 11a produces it.
- **Stone 13 (`decision_quality`).** Stone 13 grades coherence of the discrete decision; Stone 14 grades the dollar realization of that decision after frictions.
- **Stone 33 (Kelly).** Stone 33 grades whether the size was Kelly-optimal given the gap; Stone 14 grades whether the size produces positive realized return after frictions. Both can fail independently.
- **DESIGN.md Phase 5 commitment.** Stone 14 is the scoreboard machinery; the year-2 refinement (Stone 44 — "capacity-adjusted scoring with realistic retail market-impact assumptions") uses accumulated execution data to calibrate the model.

### What Stone 14 does NOT measure

- Whether the size was Kelly-optimal (Stone 33).
- Whether the belief was right (Stones 6–8 / 11a).
- Whether the action was coherent with the belief (Stone 13).
- Whether the update was evidence-grounded (Stone 12).

Only: at the agent's stated size, what fraction of nominal edge survives to the account?

### Implementation

- Pure-function checks on Contract fields + cost-model lookup.
- Lives in `src/fingym/evaluator/`.
- Cost-model is a separate component; the function signature is `realized_edge(contract, cost_model) -> float`.

### Note on "physics" vs "alpha" for the cost model

Per the cognition/verification boundary (DESIGN.md #5; physics-not-alpha from Constitution Tightening v1): the cost model is **physics for the verifier** — it encodes empirical market-microstructure facts (spreads exist, volumes are finite, impact scales with sqrt of participation rate). It does NOT encode alpha hypotheses about which names will move or how. The square-root law is an empirically observed property of how trade size translates to price impact, not a forecast. Calibrating `k` from observed execution data is allowed; using cost-model parameters to express a view on a name is not.

---

## How this document grows

Each stone that introduces new formal notation adds an entry here, organized by stone number. Cross-references:

- The **concept** entries (prose, intuitive definitions) live in [DEFINITIONS.md](DEFINITIONS.md).
- The **distilled summary** of each stone's teaching (with formula references back here) lives in [PYRAMID.md](PYRAMID.md).
- The **code implementation** lives in `src/fingym/`.

A formula entry must include: the formula or symbol, plain-language description, range/type, properties relevant to use (boundedness, identities), proof sketch where useful, and a pointer to the implementation. Future entries follow this pattern.

### Upcoming entries (parked, to be filled in as taught)

- Implied DCF (Stone 31)
- Options-implied probabilities (Stone 31)
- Kelly fraction: `f* = edge / odds_squared` (Stone 33)
- Fractional Kelly: `f_practical = k · f*` where `k ∈ [0.25, 0.5]` (Stone 33)
- Asymmetry of ruin: `recover_gain_required = drawdown / (1 − drawdown)` (intuitions.md #12)
