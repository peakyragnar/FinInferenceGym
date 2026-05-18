# Formulas — FinInferenceGym

## Purpose

A reference for the formal symbols, mathematical notation, and core formulas the project uses. Lookup for "what does this symbol mean" and "how is this computed."

Complements [DEFINITIONS.md](DEFINITIONS.md) — DEFINITIONS is the **prose glossary** (concepts, in plain language); FORMULAS is the **symbol and formula reference**. When a term has both, both files have it: DEFINITIONS for the idea, FORMULAS for the notation.

This document grows as new stones are taught. Each entry: the symbol or formula, the plain-language description, the range/type, where it's used in code, and cross-references. Entries are grouped by which stone introduces them.

The Constitution v5 reformulation (2026-05-18) removed the four-thing decomposition (Stone 7a), market-delta scoring (Stone 11a), and market-implied belief recovery (Stone 31). New v5 stones — 7b (atom of forecast), 11b (Forecast Ledger), 11c (calibration shrinkage), 11d (Tradable-Edge Action Engine / margin of safety), 11e (Market-State Baseline) — and reframings of Stones 12, 13, 14 will land here as they are taught during the v5 teaching pass.

---

## Bayesian update (Stone 1 / intuitions.md #1)

The math of belief revision. Used by the coin toy and any future inference agent.

```
P(hypothesis | evidence) = P(evidence | hypothesis) × P(hypothesis) / P(evidence)
```

In our notation:

```
P_new(h) = likelihood(evidence | h) × P_old(h) / Σ_h' [ likelihood(evidence | h') × P_old(h') ]
```

- **Inputs:** prior belief `P_old`, evidence, likelihood model.
- **Output:** posterior belief `P_new`. Distribution; sums to `1`.
- **In code:** `src/fingym/toys/coin.py:update()`.
- **Property:** if prior assigns `0` to a hypothesis, posterior is `0` forever (Cromwell).

---

## Proper scoring rules (Stones 6 and 7)

The Layer-1 math primitives. Pure functions of `(belief, outcome)`.

### Brier score

```
Brier(belief, outcome) = Σ_h (belief(h) − 1[h == outcome])²
```

For each hypothesis `h`: take the probability the agent assigned `belief(h)`, subtract `1` if `h` is the actual outcome (otherwise subtract `0`), square it, sum across all hypotheses.

- **Range:** `[0, 2]` for any number of hypotheses (binary or multi-class).
- **Min (perfect):** `0.0` when `belief(outcome) = 1` and all other probabilities are `0`.
- **Max (catastrophic):** `2.0` when `belief(outcome) = 0` and probability `1` is on a single wrong hypothesis.
- **Bounded:** does not blow up on Cromwell violations.
- **Properness proof sketch:** `E_q[Brier(r, y)]` is a quadratic in `r` with `dE/dr = 0` at `r = q`. Reporting the true belief minimizes expected loss.
- **In code:** `src/fingym/evaluator/scoring.py:brier()`.

### Log score

```
log_score(belief, outcome) = −ln(belief(outcome))
```

Take the probability the agent assigned to the actual outcome; take its natural log; flip the sign so lower = better.

- **Range:** `[0, +∞)`.
- **Min (perfect):** `0.0` when `belief(outcome) = 1`.
- **Max:** **unbounded.** `+∞` when `belief(outcome) = 0` (Cromwell violation).
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

### v5 generalization

Under v5, the agent emits a forecast distribution over realized returns rather than a belief over a hypothesis space of states. Brier and log score still apply: substitute realized return for outcome and bucketed-or-parametric forecast for belief. The math is unchanged; only the underlying object's interpretation changes.

---

## Calibration measurement (Stone 8)

Layer-2 measurement of forecast calibration across many predictions. Concrete worked example with tables in [PYRAMID.md](PYRAMID.md) Stone 8 summary.

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

For multi-class forecasts:

```
q_i = max_h forecast_i(h)                        # confidence on the agent's top guess
y_i = 1 if argmax_h forecast_i(h) == outcome_i else 0
```

Reduces multi-class to binary; bucket and score as above.

### Important property — calibration is necessary, not sufficient

An uninformative agent (always says `0.5`) can achieve low ECE when the base rate is near `0.5`. ECE alone does not detect this; pair with Brier and log score, which both punish uninformative agents.

The reliability **table** (per-bucket gap structure) is the diagnostic; ECE is the summary. A one-bucket table with low ECE is a red flag — the agent has no discrimination.

### Per-signal-class reliability (v5 extension, Stone 11b)

Under v5, calibration is measured **per signal class** by the Forecast Ledger over the agent's full history. Same bucketing math; partitioned by `signal_class_id`. The Action Engine reads `reliability_for_signal_class(signal_class_id, claimed_bucket)` at decision time to shrink the raw forecast toward empirical truth. Formal notation for the Forecast Ledger view lands here when Stone 11b is taught.

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
  signal_class_id:  str            # v5 — tag for Forecast Ledger reliability bucket

  # What the agent emitted (cognition side)
  forecast_distribution: ForecastDistribution   # F_AI(R); v5 (was BeliefDistribution = P_AI(S))

  # What the engine computed (verification side; populated by Tradable-Edge Action Engine)
  calibrated_forecast:        ForecastDistribution | None   # F_AI_calibrated after Ledger shrinkage
  calibrated_expected_utility: float | None
  tradable_edge_score:         float | None
  final_action:                ActionOrNoAction | None

  # What reality delivered (filled in at horizon)
  realized_return:  float          # R_realized at horizon (v5; was outcome = S_true)

  # Scoring columns (filled in by evaluator; grow per stone)
  brier:                 float
  log_score:             float            # may be +inf (Cromwell)
  claim_bucket:          int              # 0..9, for ECE aggregation

  # Future columns (placeholders, populated as v5 stones are taught)
  # signal_class_reliability:    float    # Stone 11b
  # process_quality_flag:        bool     # Stone 12 (v5 reframing)
  # decision_quality:            float    # Stone 13 (v5 reframing)
  # capacity_adjusted_edge:      float    # Stone 14 (v5 reframing)
  # incremental_AI_edge:         float    # Stone 11e — AI realized edge − Baseline realized edge
}
```

### Operations

- **Aggregate per column.** `mean(scoreboard.brier)`, `mean(scoreboard.log_score where not cromwell)`, etc.
- **Slice by metadata.** `scoreboard.filter(horizon=="6m").mean(brier)`, `scoreboard.filter(signal_class_id==X).mean(...)`, etc.
- **Compare agents.** Same scoreboard with `agent_id` column lets aggregations group by agent.
- **Collapse to scalar.** Only at decision points; rule must be declared and written down.

### Implementation

- Schema: `src/fingym/evaluator/scoreboard.py` (Phase 0 substep 4b/4c deliverable).
- Storage: Postgres tables per the data spine (see [memory-design.md](memory-design.md)). The `forecasts`, `realized_returns`, and `scores` tables together back the scoreboard; the Forecast Ledger view is derived from `forecasts` and `realized_returns`.
- Immutable, append-only. Aggregations computed from the immutable rows; no row updated in place.

### Connection to other stones

- Brier (Stone 6) — populates `brier` column.
- log_score (Stone 7) — populates `log_score` column.
- Calibration (Stone 8) — uses `claim_bucket` for aggregation; produces ECE per agent.
- Stones 10, 11, and the v5 stones (7b, 11b, 11c, 11d, 11e, plus reframed 12, 13, 14) each add their columns when taught.

---

## Multi-horizon scoring (Stone 10)

Realized returns are per-horizon by default. A single decision-time produces multiple `Contract` rows, one per horizon the agent cares about. The scoreboard's `horizon` column distinguishes them; per-horizon aggregations and per-horizon promotion gates fall out of slicing by that column.

### Setup

- `horizons: list[Horizon]` — configurable per evaluator run. Standard: `["1m", "3m", "6m", "1y"]`. Toys may use shorter (days or flips).
- For each decision-time `t` and each horizon `h`, the agent emits one Contract.
- `R_realized(t, h)` — the realized return as of time `t + h`. Distinct per horizon; revealed at horizon.

### Per-horizon scoring

Each Contract's evaluation columns (Brier, log_score, claim_bucket, etc.) are computed against `R_realized(t, h)` — the realized return at *that horizon*, not at the decision time.

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
    if held_out_reliability_improves(h)
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

Same forecast, different expressions = different payoff structures. The scoreboard's `expression_type` column is the **broad category** for slicing; full trade details live inside the `TradeAction` object on the Contract.

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

The category is for slicing (statistical power). The full spec is for payoff math (Stones 13 and 14 under v5; lands when reframed in teaching).

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
  signal_classes:   list[str]        # v5 — only act in signal classes where reliability holds
}
```

A skill might apply ONLY at `horizons=[3m, 6m] ∩ expression_types=[equity-long] ∩ sectors=[tech_hardware] ∩ signal_classes=[operational_leverage_q3_surprise]`. Narrowly tagged, narrowly applied. Each slicing dimension is independent.

### `NoAction` is a peer, not a sub-type

```
ActionOrNoAction = TradeAction | NoAction

NoAction { decision_time: datetime, reason: str }
```

`NoAction` has no payoff structure to evaluate. Under v5, scored separately by Stone 13 (reframed) — did the margin-of-safety gate correctly verdict `NoAction` given `calibrated_expected_utility` did not clear the threshold?

### In code

- `expression_type` field on scoreboard row.
- `TradeAction` typed in `src/fingym/agents/contract.py`.
- Per-expression-type aggregations: `scoreboard.filter(expression_type==X).mean(...)`.

---

## How this document grows

Each stone that introduces new formal notation adds an entry here, organized by stone number. Cross-references:

- The **concept** entries (prose, intuitive definitions) live in [DEFINITIONS.md](DEFINITIONS.md).
- The **distilled summary** of each stone's teaching (with formula references back here) lives in [PYRAMID.md](PYRAMID.md).
- The **code implementation** lives in `src/fingym/`.

A formula entry must include: the formula or symbol, plain-language description, range/type, properties relevant to use (boundedness, identities), proof sketch where useful, and a pointer to the implementation. Future entries follow this pattern.

### Upcoming entries (parked, to be filled in as taught during the v5 teaching pass)

- Stone 7b — atom of forecast (realized return as the predicted object; forecast distribution shape)
- Stone 11b — Forecast Ledger (per-signal-class reliability formula and SQL view definition)
- Stone 11c — calibration shrinkage (how raw forecast is shrunk toward empirical reliability)
- Stone 11d — Tradable-Edge Action Engine (calibrated expected utility; Kelly under shrunk distribution; margin-of-safety threshold)
- Stone 11e — Market-State Baseline (Track C) attribution math (incremental AI edge formula)
- Stone 12 (v5 reframing) — process-quality flag (motivated-update mechanical check)
- Stone 13 (v5 reframing) — decision quality under the margin-of-safety gate
- Stone 14 (v5 reframing) — capacity-adjusted return after Forecast-Ledger-calibrated forecast
- Kelly fraction: `f* = edge / odds_squared` (Stone 33)
- Fractional Kelly: `f_practical = k · f*` where `k ∈ [0.25, 0.5]` (Stone 33)
- Asymmetry of ruin: `recover_gain_required = drawdown / (1 − drawdown)` (intuitions.md #12)
