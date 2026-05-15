# Contract — Structured Terminal Output Specification

## TL;DR

Every cognitive output the system takes seriously must take the shape of a typed `Contract` object. The `Contract` is the bridge from unconstrained model cognition to a scoreable, market-relative, time-separated claim. **A model output that does not land in a `Contract` is prose, not alpha.**

This document is the MVP spec for the `Contract`. Required fields are buildable at Phase 0 (substep 6). Deferred fields arrive as the underlying machinery ships (cost models in Phase 2, capacity in Phase 5, etc.). Pattern matches [memory-design.md](memory-design.md): lean MVP now, deferral list with explicit triggers.

A `Contract` whose `action_or_no_action` field is `NoAction` is informally called a `NoEdgeContract`. It carries the same required fields and is scored the same way — declining to trade is itself a typed claim under audit.

---

## Purpose

This document is the source of truth for the structured terminal output. It complements:

- **[DESIGN.md](DESIGN.md)** — commitments #5 (cognition/verification boundary) and #6 (raw evidence in, structured output out), plus the four-thing decomposition (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`)
- **[TECHNICAL.md](TECHNICAL.md)** — the model interface stack (`src/fingym/agents/interface.py`) that types the contract
- **[BUILD.md](BUILD.md)** — Phase 0 substep 6 (the contract Protocol), Phase 2 (the first model-driven agent that emits real contracts)
- **[memory-design.md](memory-design.md)** — the `memory_update_proposal` field in a `Contract` is the L2 proposal that feeds the promotion gate
- **[PYRAMID.md](PYRAMID.md)** — Stones 19 (model interface contract), 11a (market-delta scoring), Layer 5 (Phase 2 mechanisms that produce the contract's market-implied fields)
- **[DEFINITIONS.md](DEFINITIONS.md)** — formal definitions of `Contract`, `NoEdgeContract`, `P_AI(S)`, `P_market(S)`, `S_true`, `Edge`

---

## What "Contract" is in this project specifically

A clarification, because "contract" is overloaded in software:

A `Contract` here is **not** a legal contract, **not** a smart-contract on a blockchain, **not** a service contract between microservices. It is the **claim contract** the agent emits at decision time, declaring what it believes, what it would trade, when the claim will be judged, and what would falsify it. The evaluator scores against future reality; the trajectory store preserves it for year-2 SFT; the promotion gate uses its calibration history to decide what enters memory.

Think of it as: *the typed terminal node of a model run, structured so the system can score, audit, and learn from it.*

---

## The MVP Contract — required fields (Phase 0)

Every `Contract` carries these fields. The Phase 0 evaluator (substep 4) scores against these. The model-interface Protocol (substep 6) types these.

```yaml
# Required at Phase 0 — minimal scoreable contract

# --- Identity and timing ---
contract_id: <uuid-string>           # stable, never reused
decision_time: <iso datetime>        # the as-of time of the decision
agent_id: <string>                   # which agent produced this
model_id: <string>                   # which model was used (Claude / GPT / Gemini / open-weights)
prompt_version: <string>             # which prompt structure (for population diversity)

# --- What the agent looked at ---
evidence_ids: list[EvidenceRef]      # pointers to L0 trajectory rows
                                     # every reference must satisfy as_known <= decision_time
                                     # (the time-leak guard for Phase 1)

# --- What the agent thinks the world is ---
hidden_state_hypotheses: list[HiddenStateHypothesis]
                                     # the model's proposed state space
                                     # the model defines this, not the system

ai_belief: BeliefDistribution        # P_AI(S) — sums to 1
                                     # never a point estimate
                                     # may include Cromwell smoothing

# --- What the agent thinks the market thinks ---
market_implied_belief: MarketBeliefEstimate | None
                                     # P_market(S) — recovered from price, options,
                                     # estimates, spreads. Phase 0: None allowed
                                     # (toy without market). Phase 2: required.

belief_delta: BeliefDelta | None     # P_AI(S) − P_market(S). Phase 0: None allowed.
                                     # Phase 2+: required when market_implied_belief is set.

# --- What the agent does ---
horizon: str                         # "1m", "2m", "3m", "6m", "1y", or custom
                                     # the horizon over which this claim is scored

action_or_no_action: TradeAction | NoAction
                                     # NoAction is a first-class output, not a degenerate case
                                     # (DESIGN.md Operational Constraints)

recommended_size: float              # fractional Kelly size; 0.0 for NoAction
                                     # bounded by sizer in Phase 2

# --- How the agent will be judged ---
falsifiers: list[Falsifier]          # what future observations would prove this wrong
                                     # must be at least 1 (a Contract without falsifiers
                                     # is unfalsifiable and rejected)

label_plan: LabelPlan                # which labels will score this, at which horizons
                                     # carries the labelling-function used to construct
                                     # labels from future emissions (PYRAMID Stone 2)

# --- How the agent thought (for VOI) ---
cognitive_audit_trail: list[CognitiveStep]
                                     # log of (initial belief, additional reasoning,
                                     # updated belief, action change) per cognitive iteration
                                     # consumed by Phase 4 VOI mechanism
                                     # at Phase 0 this is a one-step trail (no iteration)

# --- Optional memory proposal ---
memory_update_proposal: MemoryUpdateProposal | None
                                     # L2 proposal, fed to promotion gate (Phase 4)
                                     # None is fine — most contracts don't propose memory
```

### Field semantics

**`evidence_ids`** — every reference must point to an L0 trajectory row whose `as_known` is ≤ `decision_time`. The Phase 1 data spine enforces this via `time_leak_guard`. Phase 0 toys construct evidence in-memory; the guard is a no-op until L0 exists.

**`hidden_state_hypotheses`** — the model defines its own state space. There is no fixed ontology. Coarse states ("healthy / deteriorating / fraud") are fine; fine-grained states are also fine. The state space lives inside the contract, not in code.

**`ai_belief`** — a probability distribution over `hidden_state_hypotheses`. Must sum to 1 within floating-point tolerance. May not assign 0 to any hypothesis (Cromwell — see PYRAMID Stone 5). The evaluator's scoring rules (Brier, log score) operate on this field.

**`market_implied_belief`** — Phase 0 may be `None` if no market is being modeled (e.g., the coin toy). The synthetic-market toy (Stone 15) and all of Phase 2+ require this field to be populated. Phase 2 builds the recovery mechanism (Stone 31).

**`belief_delta`** — when both `ai_belief` and `market_implied_belief` are set, the delta must be computed and stored. Market-delta scoring (Stone 11a) operates on this field.

**`action_or_no_action`** — typed alternation. `NoAction` is not a special case of `TradeAction` with size = 0; it is a structurally distinct type. The verifier scores `NoAction` calls when no `TradeAction` had positive expected log-growth-after-costs. An agent that never emits `NoAction` is flagged (BIAS_PATTERNS #12).

**`recommended_size`** — fractional Kelly under model uncertainty. 0.0 for `NoAction`. The sizer (Stone 33) enforces fractional Kelly bounds; at Phase 0 the size is whatever the model emits, scored by the capacity-adjusted return metric.

**`falsifiers`** — at least one required. A contract that names no falsifier is unfalsifiable narrative, not a scoreable claim. Falsifiers may be specific (a future earnings number, a price level, a guidance change) or pattern-based (a class of evidence that would contradict the belief).

**`label_plan`** — declares what labels at what horizons will score this contract. The labelling function is part of the plan, not implicit (PYRAMID Stone 2). One contract spawns multiple labels (one per horizon).

**`cognitive_audit_trail`** — Phase 0 is one entry: `(initial_belief = ai_belief, additional_reasoning = "", action_change = false, final_belief = ai_belief)`. Phase 2+ may have multiple entries if the agent iterates (e.g., decides to fetch more evidence, updates belief, then commits). The VOI mechanism (Phase 4) reads this trail to compute "did more thinking change the action?"

---

## Deferred fields — what's queued and what triggers each

These fields are real and load-bearing once the underlying machinery exists. They are **optional in the Phase 0 schema** so that no schema migration is required when they arrive — the model just starts populating them.

| Deferred field | What it is | Phase it lands | Trigger to require |
|---|---|---|---|
| `cost_model` | Per-trade cost estimate (commissions, fees, financing, borrow) | Phase 2 | When the first model-driven agent ships and starts producing trade actions on real names |
| `slippage_model` | Per-trade slippage estimate as a function of size and liquidity | Phase 2 | Same as `cost_model` |
| `payoff_distribution` | Distribution of trade payoff conditional on each hidden state | Phase 2 | When the action search module (Stone 32 edge calculator) ships |
| `expected_value_after_costs` | Scalar EV of the action net of cost+slippage | Phase 2 | Same |
| `expected_log_growth_after_costs` | Scalar log-growth contribution of the action | Phase 2 | Same |
| `max_loss` | Worst-case loss for sized position | Phase 2 | When the sizer (Stone 33) ships |
| `capacity_estimate` | Maximum size at which edge survives market impact | Phase 5 | When capacity-adjusted scoring (Stone 44) ships |
| `liquidity_constraints` | Borrow availability, options open interest, ADV limits | Phase 2 | When the first real-name trade is emitted |
| `entry_conditions` | Conditions under which the trade is initiated | Phase 3 | When live operation starts |
| `exit_conditions` | Conditions under which the trade is closed | Phase 3 | When live operation starts |
| `correlation_haircut` | Reduction in size due to correlation with existing positions | Phase 4 | When the population mechanic produces multiple concurrent trades |
| `crowding_estimate` | Estimate of how crowded this trade is among other participants | Phase 4 | When the proposer/promotion mechanic produces enough trade volume to matter |

The principle: **build the smallest contract that the Phase 0 evaluator can score, then add fields as the consuming mechanisms ship.** The same principle as memory-design.md.

---

## What the Contract is NOT

Each line below names a failure mode the contract is explicitly designed against:

- **Not a narrative.** A contract is not a memo, thesis, or rationale. Prose belongs in `cognitive_audit_trail` (for VOI) or in proposed memory (for promotion gate review) — never in lieu of the structured fields. See BIAS_PATTERNS.md #11 (narrative as evidence).
- **Not an analyst checklist.** The contract is the OUTPUT shape, not a PROMPT template. The model decides its own reasoning sequence. See BIAS_PATTERNS.md #8 (narrowing the model interface).
- **Not a single-horizon claim.** A contract names a horizon, but the model can emit multiple contracts at different horizons for the same underlying name. Multi-horizon scoring (Stone 10) operates on these in parallel.
- **Not a portfolio recommendation.** A contract is one claim about one (name × horizon × expression). The portfolio is the aggregate of many contracts under capital constraints (Phase 3+).
- **Not promoted memory.** A contract may propose a memory update, but the proposal is `L2 probationary` until the promotion gate runs. See memory-design.md.
- **Not a P&L target.** Contracts are scored on calibration, market-delta accuracy, decision quality, and log-growth contribution — not on raw P&L. See DESIGN.md "Failure Modes" (Goodhart resistance).

---

## How the Contract relates to the four-thing decomposition

The four objects from DESIGN.md Architectural Physics map directly to contract fields:

| DESIGN.md object | Contract field |
|---|---|
| `S_true` | Never in the contract (unobservable). Known to the evaluator in toys; constructed via labelling function in real markets. |
| `P_AI(S)` | `ai_belief` |
| `P_market(S)` | `market_implied_belief` |
| `Action(A)` | `action_or_no_action` |
| `Edge = P_AI − P_market` (net of costs) | `belief_delta` (raw) + `expected_log_growth_after_costs` (cost-adjusted, Phase 2+) |

This is the structural reason the four-thing decomposition is load-bearing: it determines the contract schema.

---

## Validation

The Phase 0 evaluator (substep 4) and the model interface Protocol (substep 6) enforce:

1. `ai_belief` is a valid probability distribution (sums to 1, no negative values, no zero values on hypotheses in the support).
2. If `market_implied_belief` is set, `belief_delta` is computed and stored.
3. Every `evidence_id` resolves to an L0 row (Phase 1+; Phase 0 toys construct in-memory).
4. Every `evidence_id`'s `as_known` is ≤ `decision_time` (time-leak guard, Phase 1+).
5. `falsifiers` is non-empty.
6. `label_plan` declares at least one (label, horizon) pair.
7. `recommended_size` is 0.0 iff `action_or_no_action` is `NoAction`.
8. `horizon` is one of the registered evaluation windows (or a declared custom horizon).
9. `cognitive_audit_trail` has at least one entry (the initial belief and final belief, even if no iteration occurred).

Failing any check → the contract is rejected at the verifier gate, not scored, not persisted to the trajectory store. The agent run is recorded as a verifier-rejection in the operational log.

---

## Code layout

| Artifact | Location |
|---|---|
| Contract pydantic model | `src/fingym/agents/contract.py` (Phase 0 substep 6) |
| Contract validator | `src/fingym/agents/contract_validator.py` (Phase 0 substep 6) |
| Model interface Protocol | `src/fingym/agents/interface.py` (Phase 0 substep 6) |
| Evidence reference type | `src/fingym/agents/evidence.py` (Phase 1) |
| Trajectory row from contract | `src/fingym/data/trajectory.py` (Phase 1) |
| Contract-to-memory-proposal converter | `src/fingym/memory/proposal.py` (Phase 2) |

---

## Change control

This document is updated when:

1. **A deferred field gets activated** — its trigger fired. Move the field from the deferred table to the required-fields section. Update [TECHNICAL.md](TECHNICAL.md), the pydantic model in `src/fingym/agents/contract.py`, and the validator. Log the change in [DECISIONS.md](DECISIONS.md).
2. **A new field is added** — analogous process. Each addition requires either (a) a DESIGN.md commitment that necessitates it, or (b) evidence from a prior phase that demands it. Without one of these, the addition is rejected (BIAS_PATTERNS.md #10 — scope expansion without reason).
3. **A required field is removed or weakened** — requires explicit deliberation and Michael sign-off; logged in DECISIONS.md. The required-field list IS the load-bearing spec.

Substantive changes to this document follow the same protocol that protects DESIGN.md and memory-design.md.
