# Contract — Structured Terminal Output Specification

## TL;DR

Every cognitive output the system takes seriously must take the shape of a typed `Contract` object. The `Contract` is the bridge from unconstrained model cognition to a scoreable, time-separated, calibration-ready claim. **A model output that does not land in a `Contract` is prose, not alpha.**

This document is the MVP spec for the `Contract` under Constitution v5. Agent-emitted fields are buildable at Phase 0 (substep 6 — already shipped) plus Phase 1 NEW Cluster F (LLM agent emits v5 Contracts). Engine-computed fields (calibration, action gate) are populated by the Tradable-Edge Action Engine in Phase 1 NEW Cluster B. Deferred fields arrive as the underlying machinery ships. Pattern matches [memory-design.md](memory-design.md): lean MVP now, deferral list with explicit triggers.

A `Contract` whose final `action` field is `NoAction` is informally called a `NoEdgeContract`. It carries the same required fields and is scored the same way — declining to trade is itself a typed claim under audit.

---

## Purpose

This document is the source of truth for the structured terminal output. It complements:

- **[DESIGN.md](DESIGN.md)** — commitments #2 (forecast distribution over realized returns, calibrated empirically), #5 (cognition/verification boundary), #6 (raw evidence in, structured output out), plus the three primitives + audit layer
- **[TECHNICAL.md](TECHNICAL.md)** — the model interface stack (`src/fingym/agents/interface.py`) that types the Contract, plus the `src/fingym/ledger/`, `src/fingym/action/`, `src/fingym/baseline/` v5 component modules
- **[BUILD.md](BUILD.md)** — Phase 0 substep 6 (the Contract Protocol), Phase 1 NEW Cluster B (Tradable-Edge Action Engine populates engine-computed fields), Cluster F (first LLM agent emits real v5 Contracts)
- **[memory-design.md](memory-design.md)** — the `memory_update_proposal` field is the L2 proposal that feeds the promotion gate
- **[PYRAMID.md](PYRAMID.md)** — Stones 19 (model interface contract), 7b (atom of forecast), 11b–11e (Forecast Ledger, calibration shrinkage, action gate, Baseline)
- **[DEFINITIONS.md](DEFINITIONS.md)** — formal definitions of `Contract`, `NoEdgeContract`, `R_realized`, `F_AI`, `F_AI_calibrated`, `Action`

---

## What "Contract" is in this project specifically

A clarification, because "contract" is overloaded in software:

A `Contract` here is **not** a legal contract, **not** a smart-contract on a blockchain, **not** a service contract between microservices. It is the **claim contract** the agent emits at decision time, declaring what it forecasts, what it would trade, when the claim will be judged, and what would falsify it. The Tradable-Edge Action Engine then enriches the Contract with calibration shrinkage and action-gate verdicts. The evaluator scores against future realized returns; the trajectory store preserves it for year-2 SFT; the promotion gate uses its calibration history to decide what enters memory.

Think of it as: *the typed terminal node of a cognition run, with verifier-side calibration and gating attached, structured so the system can score, audit, and learn from it.*

---

## Cognition fields vs Verification fields

The Contract has two disjoint groups of fields:

- **Cognition fields** — populated by the agent (the AI Core). The agent emits these and never touches the verification fields.
- **Verification fields** — populated by the Tradable-Edge Action Engine (and downstream evaluator). The engine reads the cognition fields and computes these.

The cognition/verification boundary (DESIGN.md #5) is enforced at the code level: `src/fingym/agents/` cannot write the verification fields, and `src/fingym/action/` cannot rewrite the cognition fields.

---

## The MVP Contract — required fields (Phase 0 + Phase 1 NEW)

Every `Contract` carries these fields. Cognition fields land at Phase 0 (Contract Protocol) and become populated by a real LLM at Phase 1 NEW Cluster F. Verification fields become populated at Phase 1 NEW Cluster B (Tradable-Edge Action Engine).

```yaml
# Required at Phase 0 + Phase 1 NEW — minimal scoreable v5 contract

# --- Identity and timing ---
contract_id: <uuid-string>           # stable, never reused
decision_time: <iso datetime>        # the as-of time of the decision
agent_id: <string>                   # which agent produced the cognition fields
model_id: <string>                   # which model was used (Claude / GPT / Gemini / open-weights)
prompt_version: <string>             # which prompt structure (for population diversity)

# --- COGNITION FIELDS (agent-emitted) ---

# What the agent looked at
evidence_ids: list[EvidenceRef]      # pointers to L0 trajectory rows
                                     # every reference must satisfy as_known <= decision_time
                                     # (the time-leak guard for Phase 1)
data_sources_used: list[str]         # explicit categorization of source types consumed
                                     # e.g., ["transcript", "10K", "headline_observables"]

# What the agent forecasts
forecast_distribution: ForecastDistribution
                                     # F_AI(R) — distribution over realized return for this
                                     # (name, horizon, expression-type). Sums to 1; no zero
                                     # probabilities on values in the support (Cromwell).
signal_class_id: str                 # tag for the Forecast Ledger's reliability bucket
                                     # the agent classifies its own forecast into a signal class
                                     # (e.g., "operational_leverage_q3_surprise", "supply_chain_disruption")
                                     # the Ledger tracks per-signal-class reliability over many forecasts
thesis_category: str                 # broader categorization for analytics and memory tagging
                                     # finer than signal_class_id

# What the agent recommends (raw — engine may override)
horizon: str                         # "1m", "2m", "3m", "6m", "1y", or custom
recommended_action: TradeAction | NoAction
                                     # the agent's raw action recommendation
                                     # engine verifies/gates and produces final_action below
recommended_size: float              # fractional Kelly size from the agent's perspective; 0.0 for NoAction
                                     # engine recomputes after calibration

# How the agent will be judged
falsifiers: list[Falsifier]          # what future observations would prove the forecast wrong
                                     # must be at least 1
realized_return_plan: RealizedReturnPlan
                                     # which realized returns at which horizons will score this Contract
                                     # carries the labelling function (simple vs log return, expression-specific
                                     # payoff structure) used to construct realized returns

# How the agent thought (for VOI; Phase 4 mechanism consumes)
cognitive_audit_trail: list[CognitiveStep]
                                     # log of (initial forecast, additional reasoning, updated forecast,
                                     # action change) per cognitive iteration

# Optional memory proposal
memory_update_proposal: MemoryUpdateProposal | None
                                     # L2 proposal, fed to promotion gate (Phase 4)

# --- VERIFICATION FIELDS (Tradable-Edge Action Engine; Phase 1 NEW Cluster B) ---

calibrated_forecast: ForecastDistribution | None
                                     # F_AI_calibrated — agent's raw forecast shrunk toward
                                     # per-signal-class empirical reliability from the Forecast Ledger
                                     # None at Phase 0 (engine not yet built)
                                     # Required from Phase 1 NEW Cluster B onward
calibrated_expected_return: float | None
                                     # E[R_realized | F_AI_calibrated] — expected value under shrunk distribution
calibrated_expected_utility: float | None
                                     # Kelly-equivalent calibrated EU under the shrunk distribution and cost model
tradable_edge_score: float | None    # calibrated_expected_utility minus margin-of-safety threshold
                                     # positive → trade gate clears; non-positive → NoAction
kelly_fraction_applied: float | None # the engine's final sizing (may differ from recommended_size)
cost_estimate: CostEstimate | None   # spread + commission + impact + alpha decay used in the gate
final_action: TradeAction | NoAction | None
                                     # the engine's verdict; may differ from recommended_action if the gate
                                     # doesn't clear. This is the action scored downstream.
```

### Field semantics

**`evidence_ids`** — every reference must point to an L0 trajectory row whose `as_known` is ≤ `decision_time`. The Phase 1 NEW data spine (Cluster E for toy; Phase 2 NEW for real) enforces this via `time_leak_guard`. Phase 0 toys construct evidence in-memory; the guard is a no-op until L0 exists.

**`data_sources_used`** — an explicit list of source-type tags. Used by the evaluator for slicing (e.g., "is this agent's edge in transcript-driven forecasts or in fundamentals-driven forecasts?") and by the promotion gate's survivorship check.

**`forecast_distribution`** — `F_AI(R)`. A probability distribution over realized returns for the (name, horizon, expression-type). Representation: parametric (e.g., Gaussian, Student-t with named parameters), nonparametric (e.g., bucketed PMF), or quantile-based. Must sum/integrate to 1. May not assign 0 to any value in the support (Cromwell).

**`signal_class_id`** — the agent classifies its own forecast into a signal class (a string identifier). The Forecast Ledger maintains per-signal-class empirical reliability. The Tradable-Edge Action Engine reads this id at decision time to look up the reliability for shrinkage. Signal classes are a SEARCHABLE element (DESIGN.md "Searchable vs Architectural") — the agent proposes them; the Ledger tracks them; new classes emerge from agent cognition without architectural change.

**`thesis_category`** — finer-grained than `signal_class_id`. Used for memory tagging and population diversity tracking. Not used by the calibration shrinkage step.

**`recommended_action`** — the agent's raw action recommendation. `TradeAction` carries the proposed expression (equity-long, option-call, etc.), strike/expiration if applicable, direction, and proposed size. `NoAction` carries a reason. **The agent's recommendation is not the final action**; the Tradable-Edge Action Engine may override it (e.g., shrink it to `NoAction` if calibrated EU doesn't clear margin-of-safety).

**`final_action`** — the engine's verdict after calibration + gate. This is what gets scored downstream.

**`falsifiers`** — at least one required. A Contract that names no falsifier is unfalsifiable narrative, not a scoreable claim.

**`realized_return_plan`** — declares the labelling function for realized returns (simple vs log, total-return vs price-return, expression-specific payoff structure for options/vol/pairs) and the horizons at which it applies.

**`cognitive_audit_trail`** — Phase 0 is one entry: `(initial_forecast = forecast_distribution, additional_reasoning = "", action_change = false, final_forecast = forecast_distribution)`. Phase 1 NEW Cluster F+ may have multiple entries if the LLM iterates. The VOI mechanism (Phase 4) reads this trail.

**`calibrated_forecast`** — `F_AI_calibrated`. The Tradable-Edge Action Engine computes this by shrinking `forecast_distribution` toward the per-signal-class reliability from the Forecast Ledger. Phase 0: `None` (engine not yet built). Phase 1 NEW Cluster B+: required.

**`calibrated_expected_utility`** — Kelly-equivalent EU under `calibrated_forecast` and `cost_estimate`. Computed by the Action Engine.

**`tradable_edge_score`** — `calibrated_expected_utility − margin_of_safety_threshold`. Positive → the gate clears and `final_action` is a `TradeAction`. Non-positive → the gate does NOT clear and `final_action` is `NoAction`. This single signed scalar is the action-gate verdict.

**`kelly_fraction_applied`** — the engine's final size after Kelly under the shrunk distribution. May differ from `recommended_size`.

**`cost_estimate`** — the cost model used (spread + commission + impact + alpha decay). Populated by the engine, not by the agent.

**`final_action`** — the engine's action verdict. The agent's `recommended_action` is the cognitive output; `final_action` is the verification output. Scoring downstream uses `final_action`.

---

## Deferred fields — what's queued and what triggers each

These fields are real and load-bearing once the underlying machinery exists. They are **optional in the v5 schema** so that no schema migration is required when they arrive — the engine just starts populating them.

| Deferred field | What it is | Phase it lands | Trigger to require |
|---|---|---|---|
| `payoff_distribution` | Distribution of trade payoff conditional on each value of realized return | Phase 1 NEW Cluster B | When the Action Engine computes calibrated EU on real expressions |
| `max_loss` | Worst-case loss for sized position | Phase 1 NEW Cluster B | When the sizer applies a fractional Kelly bound |
| `capacity_estimate` | Maximum size at which edge survives market impact | Phase 5 | When capacity-adjusted scoring ships |
| `liquidity_constraints` | Borrow availability, options open interest, ADV limits | Phase 2 NEW | When the first real-name trade is emitted |
| `entry_conditions` | Conditions under which the trade is initiated | Phase 3 | When live operation starts |
| `exit_conditions` | Conditions under which the trade is closed | Phase 3 | When live operation starts |
| `correlation_haircut` | Reduction in size due to correlation with existing positions | Phase 4 | When the population mechanic produces multiple concurrent trades |
| `crowding_estimate` | Estimate of how crowded this trade is among other participants | Phase 4 | When the proposer/promotion mechanic produces enough trade volume to matter |
| `baseline_forecast_reference` | Pointer to the parallel Market-State Baseline forecast for this (name, horizon, expression) — for attribution joins | Phase 1 NEW Cluster I | When the toy Baseline produces parallel rows for the same (name, horizon, expression) |

The principle: **build the smallest contract that the v5 evaluator + Action Engine can score, then add fields as the consuming mechanisms ship.** The same principle as memory-design.md.

---

## What the Contract is NOT

Each line below names a failure mode the contract is explicitly designed against:

- **Not a narrative.** A Contract is not a memo, thesis, or rationale. Prose belongs in `cognitive_audit_trail` (for VOI) or in proposed memory (for promotion gate review) — never in lieu of the structured fields. See BIAS_PATTERNS.md #11 (narrative as evidence).
- **Not an analyst checklist.** The Contract is the OUTPUT shape, not a PROMPT template. The model decides its own reasoning sequence. See BIAS_PATTERNS.md #8 (narrowing the model interface).
- **Not a single-horizon claim.** A Contract names a horizon, but the model can emit multiple Contracts at different horizons for the same underlying name. Multi-horizon scoring (Stone 10) operates on these in parallel.
- **Not a portfolio recommendation.** A Contract is one claim about one (name × horizon × expression). The portfolio is the aggregate of many Contracts under capital constraints (Phase 3+).
- **Not promoted memory.** A Contract may propose a memory update, but the proposal is `L2 probationary` until the promotion gate runs. See memory-design.md.
- **Not a P&L target.** Contracts are scored on calibration, per-signal-class reliability, tradable-edge accuracy, decision quality, and log-growth contribution — not on raw P&L. See DESIGN.md "Failure Modes" (Goodhart resistance).
- **Not an unverified forecast.** The action gate operates on `calibrated_forecast` (the Action Engine's shrunk version), not on `forecast_distribution` (the agent's raw output). An agent whose `final_action` clears the gate without calibration shrinkage having been applied is a verifier-rejection event.
- **Not a Baseline-aware emission.** The Contract's cognition fields are produced by the AI Core, which by code-level isolation never sees the Market-State Baseline's processed forecast. `baseline_forecast_reference` (deferred) is a pointer only, populated by the engine for attribution joins.

---

## How the Contract relates to the three primitives plus audit layer

The three primitives from DESIGN.md "Architectural Physics" map directly to Contract fields:

| DESIGN.md object | Contract field |
|---|---|
| `R_realized` | Never in the Contract at decision time (unobservable). Stored separately in `realized_returns` table at horizon; joined to the Contract for scoring. |
| `F_AI(R)` | `forecast_distribution` |
| `Action(A)` | `recommended_action` (agent-emitted, raw) → `final_action` (engine's verdict after calibration + gate) |
| `F_AI_calibrated` | `calibrated_forecast` |
| Margin-of-safety gate verdict | `tradable_edge_score` (signed; positive → trade; non-positive → NoAction) |

Audit-layer attribution objects:

| DESIGN.md object | Where it lives |
|---|---|
| `F_baseline(R)` | NOT in the Contract — produced separately by `src/fingym/baseline/` and stored in the `forecasts` table tagged `agent_id = 'baseline'`. The Contract's `baseline_forecast_reference` (deferred field) can point to it for join. |
| `Incremental_AI_edge` | A scoreboard column computed from this Contract's `final_action` realized edge minus the Baseline's parallel realized edge. Not a Contract field; it's downstream. |

The structural reason v5 primitives shape the Contract: the action chain (cognition → calibration → gate → action) operates within a single Contract, while the Baseline runs in parallel and is joined for attribution downstream.

---

## Validation

The Phase 0 evaluator (substep 4) and the model interface Protocol (substep 6) enforce the cognition-side validation. The Phase 1 NEW Cluster B engine enforces the verification-side validation.

**Cognition-side validation** (applied to the agent's raw emission):

1. `forecast_distribution` is a valid probability distribution (sums/integrates to 1, no negative values, no zero values on points in the support).
2. `signal_class_id` is non-empty.
3. Every `evidence_id`'s `as_known` is ≤ `decision_time` (time-leak guard; Phase 1+).
4. `falsifiers` is non-empty.
5. `realized_return_plan` declares at least one (horizon, labelling rule) pair.
6. `recommended_size` is 0.0 iff `recommended_action` is `NoAction`.
7. `horizon` is one of the registered evaluation windows (or a declared custom horizon).
8. `cognitive_audit_trail` has at least one entry.

**Verification-side validation** (applied after the engine runs):

9. If `calibrated_forecast` is set, it is also a valid probability distribution (same shape constraints as `forecast_distribution`).
10. `tradable_edge_score` ≥ 0 iff `final_action` is a `TradeAction`. `tradable_edge_score` < 0 iff `final_action` is `NoAction`.
11. `kelly_fraction_applied` is 0.0 iff `final_action` is `NoAction`.
12. The engine's `cost_estimate` is populated whenever `final_action` is a `TradeAction`.

Failing any check → the Contract is rejected at the verifier gate, not scored, not persisted as a valid trajectory row. The rejection is recorded in the operational log.

---

## Code layout

| Artifact | Location |
|---|---|
| Contract pydantic model | `src/fingym/agents/contract.py` (Phase 0 substep 6; v5 cleanup pass restructures fields) |
| Contract validator (cognition side) | `src/fingym/agents/contract_validator.py` (Phase 0 substep 6; v5 cleanup updates checks) |
| Contract validator (verification side) | `src/fingym/action/validator.py` (Phase 1 NEW Cluster B) |
| Model interface Protocol | `src/fingym/agents/interface.py` (Phase 0 substep 6) |
| Evidence reference type | `src/fingym/agents/evidence.py` (Phase 1) |
| Trajectory row from Contract | `src/fingym/data/trajectory.py` (Phase 1) |
| Contract-to-memory-proposal converter | `src/fingym/memory/proposal.py` (Phase 2) |
| Tradable-Edge Action Engine | `src/fingym/action/engine.py` (Phase 1 NEW Cluster B) |

---

## Change control

This document is updated when:

1. **A deferred field gets activated** — its trigger fired. Move the field from the deferred table to the required-fields section. Update [TECHNICAL.md](TECHNICAL.md), the pydantic model in `src/fingym/agents/contract.py`, and the validator. Log the change in [DECISIONS.md](DECISIONS.md).
2. **A new field is added** — analogous process. Each addition requires either (a) a DESIGN.md commitment that necessitates it, or (b) evidence from a prior phase that demands it. Without one of these, the addition is rejected (BIAS_PATTERNS.md #10 — scope expansion without reason).
3. **A required field is removed or weakened** — requires explicit deliberation and Michael sign-off; logged in DECISIONS.md. The required-field list IS the load-bearing spec.

Substantive changes to this document follow the same protocol that protects DESIGN.md and memory-design.md.
