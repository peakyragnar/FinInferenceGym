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

## The atom of forecast (Stone 7b)

The three primitives every v5 decision separates, plus the calibrated derivation.

### `R_realized`

- **What:** the realized log return for the `(name, horizon, expression-type)`.
- **Type:** real number. Typically in `[-1, +1]` for equities at short-to-medium horizons; unbounded in principle (`-∞` for total loss; large positive for long-horizon multibaggers).
- **Visibility:** not known at decision time. Revealed at the horizon by the labelling function (future price + corporate actions + payoff structure → realized log return).
- **Per-horizon:** `R_realized(name, horizon=3m)` and `R_realized(name, horizon=1y)` are distinct objects; scored independently.

### `F_AI(R)`

- **What:** the agent's forecast distribution over `R_realized` for a specific `(name, horizon, expression-type)`.
- **Type:** function mapping realized-return bucket label → probability in `[0, 1]`. Values sum to exactly `1`.
- **In code:** `ForecastDistribution` pydantic model in `src/fingym/agents/contract.py`; `probabilities: dict[str, float]` where the key is the bucket label (e.g., `"below_minus_5_pct"`, `"plus_5_to_plus_10_pct"`).
- **Constraint:** Cromwell — no bucket in the declared support may have probability `0`. The validator (`src/fingym/agents/contract_validator.py`) enforces this at the cognition-side check.

### `Action`

- **What:** the agent's chosen action. Discriminated union over `action_type`.
- **Type:** `TradeAction(...)` or `NoAction`. Peers, not sub-types.
- `TradeAction` carries: `expression_type` (equity-long, option-call, ...), `underlying`, `direction`, `size`, `notional`, plus options-specific fields (`strike`, `expiration`, `premium_per_unit`) where applicable.
- `NoAction` carries: `reason`. Scored under v5 by `tradable_edge_score ≤ 0` (the action-gate verdict).
- **In code:** typed sum `ActionOrNoAction = Annotated[TradeAction | NoAction, Field(discriminator="action_type")]`.

### `F_AI_calibrated(R)`

- **What:** the agent's raw `F_AI` shrunk toward per-signal-class empirical reliability from the Forecast Ledger.
- **Type:** same shape as `F_AI` (probability distribution over realized return buckets; sums to 1; no zeros).
- **Where it lives in code:** populated by the Tradable-Edge Action Engine; stored on the Contract as the `calibrated_forecast` field. `None` at Phase 0 (engine not yet built); required from Phase 1 NEW Cluster B onward.
- **Formal shrinkage rule:** the specific shrinkage formula (how the raw distribution gets pulled toward empirical reliability as a function of sample size in the Forecast Ledger) lands in Stone 11c when that stone is taught.

### Anchor sentence

> Money lives in the agent's forecast only when its calibrated expected utility (computed under `F_AI_calibrated` and the cost model) clears the margin-of-safety threshold, AND the realized return `R_realized` validates the side the agent took.

Four conditions, all required:
1. **Discriminating.** `F_AI` is non-trivially shaped (not uniform across buckets).
2. **Reliable.** The agent has accumulated empirical reliability in the signal class (Forecast Ledger has enough samples that shrinkage isn't pulling the forecast to flat).
3. **Clears the gate.** Calibrated expected utility under `F_AI_calibrated` (after costs and capacity) exceeds the margin-of-safety threshold (Stone 11d).
4. **Validated.** Realized `R_realized` lands consistently with the forecast's leaning.

If any link fails, no edge.

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

## Capacity-adjusted realized return (Stone 14, Constitution v5)

The scoreboard's backward-looking edge column: what the trade actually netted after frictions actually paid at deployable size. Distinct from Stone 11d's forward-looking `calibrated_expected_utility`.

### The decomposition

```
realized_edge = nominal_payoff − spread − commission − market_impact − alpha_decay
```

All terms in fractional units (0.01 = 1%):

| Term | Formula | Source |
|---|---|---|
| `nominal_payoff` | `realized_return × direction` | realized_return from labelling function (Stone 2); direction ∈ {+1, −1} from `TradeAction.direction` |
| `spread` | `spread_bps × 1e-4` | structured cost model field |
| `commission` | `commission_bps × 1e-4` | structured cost model field |
| `market_impact` | `impact_coefficient × sqrt(notional / adv)` | sqrt-law (Kyle 1985; Almgren-Chriss) |
| `alpha_decay` | `alpha_decay_bps_per_period × horizon_periods × 1e-4` | linear in periods held |

### Direction sign

```
direction = +1   if action.direction == "long"
direction = −1   if action.direction == "short"
direction =  0   if NoAction  (-> realized_edge = 0)
```

### Square-root impact law

```
market_impact = impact_coefficient × sqrt(notional / adv)
```

Convex in size: doubling notional multiplies impact by `sqrt(2) ≈ 1.41`, not by 2. Calibration: toy MVP `impact_coefficient = 0.005` (50 bps per √ADV).

### Range and type

- `realized_edge ∈ ℝ`, sign-bearing. Positive = profitable trade after costs; negative = friction-eater or wrong-direction trade.
- For NoAction Contracts: `realized_edge = 0` exactly (no trade, no costs, no payoff).

### Properties

- **Backward-looking.** Distinct from Stone 11d's `calibrated_expected_utility = |E[r_calibrated]| − round_trip_cost_at(...)`. The pair forms a calibration audit at the agent level.
- **Convex in size via sqrt-impact.** Total edge can flip sign at large size even when small-size edge is positive.
- **Sliced primarily by deployable size bucket.** Aggregation `mean(realized_edge | size_bucket)` per agent, per signal class.
- **Near-tautological structural check:** `mean(realized_edge | size == stated_deployable_size)` across many trades must be `> 0`. Column-level threshold, not per-trade.

### Connection to Stone 11d

Same structured cost model, two directions:

```
# Stone 11d (forward-looking, decision time)
round_trip_cost_at(notional, horizon_periods)
  = spread + commission + impact_coefficient × sqrt(notional/adv)
  + alpha_decay_bps_per_period × horizon_periods × 1e-4

# Stone 14 (backward-looking, scoreboard time)
realized_edge = realized_return × direction − round_trip_cost_at(notional, horizon_periods)
```

Stone 11d gates on `tradable_edge_score = |E[r_calibrated]| − round_trip_cost_at(...) − margin_of_safety_threshold`. Stone 14 measures the same components against the realized return.

### In code

- `src/fingym/evaluator/realized_edge.py` — `realized_edge(action, realized_return, cost_model, horizon_periods) -> float`. Returns 0 for NoAction.
- `src/fingym/action/action_engine.py` — structured `ToyCostModel(adv, spread_bps, commission_bps, impact_coefficient, alpha_decay_bps_per_period)` with `round_trip_cost_at(notional, horizon_periods)` method.
- Scoreboard column `realized_edge: float` populated per Contract.

---

## How this document grows

Each stone that introduces new formal notation adds an entry here, organized by stone number. Cross-references:

- The **concept** entries (prose, intuitive definitions) live in [DEFINITIONS.md](DEFINITIONS.md).
- The **distilled summary** of each stone's teaching (with formula references back here) lives in [PYRAMID.md](PYRAMID.md).
- The **code implementation** lives in `src/fingym/`.

A formula entry must include: the formula or symbol, plain-language description, range/type, properties relevant to use (boundedness, identities), proof sketch where useful, and a pointer to the implementation. Future entries follow this pattern.

## Stone 38 — population variants (toy mode, Constitution v5)

The population is a tuple of `LlmAgentVariant(name, model, prompt_style)` configurations that run in parallel on the same emission stream. Each variant's `name` becomes the `agent_id` on its Scoreboard rows so the gate can slice by variant.

### Cluster H default population

```
DEFAULT_VARIANTS = (
    LlmAgentVariant("haiku_default",        model="claude-haiku-4-5-20251001", prompt_style=""),
    LlmAgentVariant("haiku_value_investor", model="claude-haiku-4-5-20251001", prompt_style=<value-investor framing>),
    LlmAgentVariant("sonnet_default",       model="claude-sonnet-4-6",         prompt_style=""),
)
```

3 variants; ~$0.10 per integration-test run.

### `build_population` contract

```
build_population(variants: tuple[LlmAgentVariant, ...] = DEFAULT_VARIANTS,
                 promoted_skills: list[MemoryArtifact] | None = None)
    -> list[LlmAgent]
```

Returns one `LlmAgent` per variant. Each LlmAgent's `name` matches its variant's `name`. The same `promoted_skills` list is injected into every variant (operator can pass different subsets per variant by calling once per subset).

### In code

- `src/fingym/memory/population.py` — `LlmAgentVariant`, `DEFAULT_VARIANTS`, `build_population`, `HAIKU_MODEL`, `SONNET_MODEL`.
- `src/fingym/llm/anthropic.py` — `AnthropicClient` accepts `prompt_style: str = ""` field, appended to base system prompt.

---

## Stone 40 — promotion gate (toy mode, Constitution v5)

The four-check gate decides whether a proposed memory item graduates to L3. After Cluster H, checks 1, 2, and 4 are wired up with real evaluation; check 3 is stubbed `passed=False` (honest audit — see [DECISIONS.md "Honest stubs in the toy-mode promotion gate"](DECISIONS.md)). Toy-mode promotion to L3 requires checks 1 AND 2 AND 4 to pass; an L2 (probationary) tier catches proposals that pass checks 1 + 4 but not the cross-model threshold of check 2.

### Check 1 — held-out replay (toy interpretation)

```
calibration_delta = mean(brier | overall scoreboard)
                  − mean(brier | signal_class_id == proposal.signal_class_id)
```

Passes if **both**:

```
len(rows where signal_class_id == proposal.signal_class_id) ≥ MIN_HELD_OUT_ROWS  (= 10)
calibration_delta ≥ MIN_CALIBRATION_DELTA                                        (= 0.01)
```

Forecasts tagged with the proposal's `signal_class_id` must beat the agent's overall calibration by ≥ 1 Brier-point of improvement over a sample of ≥ 10 historical forecasts. Both thresholds are operator-tunable module constants. Real LLM-replay (re-run the model with the skill in the prompt; measure improvement) is Phase 2 NEW.

### Check 4 — domain-of-validity declared (toy interpretation)

```
proposal.signal_class_id ≠ ""  AND  len(proposal.horizons) > 0
```

Literal: the proposal must carry a non-empty signal class and at least one horizon.

### Check 2 — cross-model regression (toy interpretation; Cluster H)

Run check 1 inside each variant's slice of the Scoreboard. Count the variants where check 1 passes:

```
variants_passing = [agent_id for agent_id in scoreboard.unique_agent_ids
                    if check_1_within_variant(agent_id).passed]

check_2_passed = len(variants_passing) >= MIN_VARIANTS_PASSING  (= 2)
```

The `CrossModelRegressionResult.models_validated` field carries the agent_ids of the confirming variants.

### Promotion decision (toy mode, Cluster H)

```
if not check_4_passed: return None
if not variants_passing: return None
if check_1_passed AND check_2_passed AND check_4_passed:
    return L3 MemoryArtifact
else:  # check_4 passed AND ≥1 variant confirmed AND check_2 below threshold
    return L2 MemoryArtifact (probationary)
```

Check 3 is stubbed `passed=False` and excluded from the decision. Phase 2 NEW wires up real check 3.

### Re-validation (Cluster H)

Fires every `REVALIDATION_INTERVAL_ROWS = 50` new Scoreboard rows:

```
for artifact in L3:
    rerun check 1 + 2 + 4 against current scoreboard
    if any fails: demote to L2 (audit_trail records demotion)

for artifact in L2 (where status != retired):
    rerun check 1 + 2 + 4 against current scoreboard
    if all pass: promote to L3 (audit_trail records promotion)
    elif L2 cycles count >= MAX_L2_CYCLES (= 5): retire
```

### In code

- `src/fingym/memory/promotion.py` — `evaluate_proposal(proposal, scoreboard)` (Cluster G; single-agent gate) + `evaluate_proposal_cross_model(proposal, scoreboard, min_variants_passing=2)` (Cluster H; per-variant + cross-model).
- `src/fingym/memory/revalidation.py` — `revalidate(scoreboard, l3_dir, l2_dir, min_variants_passing, max_l2_cycles) → RevalidationReport`.
- Module constants: `MIN_HELD_OUT_ROWS = 10`, `MIN_CALIBRATION_DELTA = 0.01`, `DEFAULT_MIN_VARIANTS_PASSING = 2`, `REVALIDATION_INTERVAL_ROWS = 50`, `MAX_L2_CYCLES = 5`.

---

### Upcoming entries (parked, to be filled in as taught during the v5 teaching pass)

- Stone 11b — Forecast Ledger (per-signal-class reliability formula and SQL view definition)
- Stone 11c — calibration shrinkage (how raw forecast is shrunk toward empirical reliability)
- Stone 11d — Tradable-Edge Action Engine (calibrated expected utility; Kelly under shrunk distribution; margin-of-safety threshold)
- Stone 11e — Market-State Baseline (Track C) attribution math (incremental AI edge formula)
- Stone 12 (v5 reframing) — process-quality flag (motivated-update mechanical check)
- Stone 13 (v5 reframing) — decision quality under the margin-of-safety gate
- Kelly fraction: `f* = edge / odds_squared` (Stone 33)
- Fractional Kelly: `f_practical = k · f*` where `k ∈ [0.25, 0.5]` (Stone 33)
- Asymmetry of ruin: `recover_gain_required = drawdown / (1 − drawdown)` (intuitions.md #12)
