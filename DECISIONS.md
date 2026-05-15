# Decisions Considered and Rejected

A log of options that were proposed (by Claude, by Michael, or by frameworks under consideration) and explicitly rejected during design, with the reasoning. This file exists so future Claude sessions do not re-propose patterns that were already evaluated and ruled out.

Every entry: **what was proposed → why rejected → principle / commitment involved.**

---

## Framework-level rejections

### David Silver-style RL (no priors) as the main path
- **Proposed**: Use AlphaGo-Zero-style RL with no human priors as the primary learning mechanism.
- **Rejected because**: works for games (infinite self-play, fully observable state, unambiguous reward). Finance has none of these. The "no priors" stance throws away genuinely load-bearing priors (Kelly, calibration, proper scoring) that took ~100 years to discover and that the system needs anyway.
- **Use selectively** on narrow sub-problems where human priors are weak. Not the main path.
- **Principle**: DESIGN.md "Architectural Physics" — useful priors are baked in as scaffolding.

### General RL as the foundation
- **Proposed**: RL as the primary mechanism for learning the agent.
- **Rejected because**: sample-inefficient, reward-hackable, opaque. Reward signal in finance is noisy and confounded (luck vs skill vs timing). RL on raw P&L is catastrophic.
- **Use later** for sequential sub-problems (when to stop researching, how to size given uncertainty) once the evaluator is rock-solid. Not foundational.
- **Principle**: DESIGN.md #1 — evaluator is load-bearing; everything else is downstream.

### AlphaEvolve as a separate framework to import
- **Proposed**: Use AlphaEvolve as the search mechanism over candidate artifacts.
- **Rejected because**: the population + promotion architecture in BUILD.md *is* AlphaEvolve over agents — we instantiate the pattern, we don't import the framework.
- **Principle**: DESIGN.md #9 — population is the unit of search.

### Continual Harness as a separate framework to import
- **Proposed**: Use Continual Harness for online refinement during long episodes.
- **Rejected because**: the LLM-as-proposer + memory + promotion-gate architecture is Continual Harness simplified. Same pattern, smaller package.
- **Principle**: Use the pattern, not the framework.

### Garry Tan multi-model committee / jury
- **Proposed**: Multi-model jury (writer / auditor / context scout) anchored to source of truth, with "skillify the fix" + cross-modal scoring.
- **Rejected because**:
  - Mostly redundant with RAG + promotion gates already in our design.
  - A jury of models all trained on emission-level data hallucinate together — "diversity" is cosmetic.
  - In finance, the better pattern is *specialist pipelines* (transcript NLP, fundamental math, options pricing), not juries.
- **Principle**: DESIGN.md #5/#6 — cognition stays in the model; rigor stays in the system. Doesn't need a committee.

### RL on raw P&L
- **Proposed (early framing)**: Reward = realized P&L from trading.
- **Rejected because**: rewards luck. Markets are noisy. A wrong belief can make money; a right belief can lose money. RL on raw P&L produces a confident reward-hacker.
- **Replacement**: Reward = scoreboard (calibration, process quality, capacity-adjusted return, etc.) — never raw P&L alone.
- **Principle**: DESIGN.md #1 — evaluator load-bearing; #2 — belief over hidden state.

### Fine-tuning the base model on finance data as main learning mechanism
- **Proposed (early framing)**: SFT or fine-tune a model on finance corpus as the primary "intelligence."
- **Rejected because**: locks the system to one model. Cannot ride the exponent. Dies the moment a better base model arrives.
- **Replacement**: Intelligence lives in architecture (memory, hypothesis registry, evaluator, promotion gate) — model is a swappable engine. Year-2 fine-tune on verified trajectories is a planned trajectory, but it's *one population member*, not the system.
- **Principle**: DESIGN.md #7 — intelligence in architecture, not weights/prompts.

### LLM-as-narrow-tool architecture
- **Proposed (early framing)**: LLM called for narrow tasks (classify transcript tone 1-5, extract a feature). Most "intelligence" in declarative artifacts hand-engineered.
- **Rejected because**: bottlenecks the model. Uses 5% of capability. When the model gets 10× better, the system gets 50% better, not 10×. Defeats the ride-the-exponent goal.
- **Replacement**: Model is the cognitive engine. Sees raw evidence. Reasons natively. Free at the cognition side; structured at the terminal output. Constraints migrate to the verification side, never sit on cognition.
- **Principle**: DESIGN.md #5/#6.

### Closed-box end-to-end systems
- **Proposed**: Treat the system as a black box that ingests data and produces trades.
- **Rejected because**: Michael must synthesize. Opacity defeats him. Non-stationarity and reflexivity make opaque systems impossible to reason about across regimes.
- **Principle**: DESIGN.md "Out of Scope."

---

## Universe-shape bias attempts

### AI-dispersion thematic universe
- **Proposed (by Claude)**: Barbell the universe across "AI beneficiaries" and "AI-disrupted incumbents" because Michael had high conviction in this thesis.
- **Caught by Michael's audit.** Rejected because: a thematic prior baked into universe selection is bias-import. If the dispersion thesis is true, the system should *discover* it from data, not be shaped around it. If it's false or overstated, we want to know — which we can't if we've pre-encoded it.
- **Principle**: DESIGN.md "Operational Constraints" — universe selection by operational/structural criteria only. Themes are outputs, not inputs.

### Concentration over breadth (operational universe ~30-50)
- **Implicit in early BUILD.md**: ~30-50 production names. Reflected Michael's discretionary trading style.
- **Caught by Michael's self-audit.** Rejected because: concentration was Michael's *preference*, not a structural necessity. The architecture can support ~1700+ analytically.
- **Replacement**: ~30 names is a *learning universe* for evaluator validation. Production analytical universe is broad (~1700+ from transcript corpus + delisted shadow). Active capital universe is emergent, bounded by where calibrated edge × capacity × Kelly justifies action.
- **Principle**: DESIGN.md "Operational Constraints" — narrowing production universe by preference is bias-import.

### Universe shaped by Michael's current names
- **Proposed (early framing)**: Pick the names Michael currently trades.
- **Rejected because**: anchors universe to Michael's discretion. Universe selection is by operational/structural criteria only.
- **Principle**: DESIGN.md #10.

### Universe limited by transcript availability
- **Initial framing**: ~30 names where transcripts were obtainable from public sources.
- **Refined when Michael revealed the 1700-name corpus.** Universe now constrained by operational/structural criteria, not by data acquisition.

---

## Action-space bias attempts

### Long-horizon-only scoring
- **Implicit in early BUILD.md**: holding periods of quarters to years.
- **Caught by Michael**. Rejected because: pre-committing to a single horizon is bias-import. Different agents may have edge at different horizons.
- **Replacement**: Multi-horizon scoring (1m / 3m / 6m / 1y) in parallel from day 1. System discovers empirically where edge lives.
- **Principle**: DESIGN.md "Out of Scope" — pre-committed time horizon.

### Single-name directional only
- **Implicit in early BUILD.md**.
- **Caught by Michael**. Rejected because: cross-sectional (pairs / relative-value) bets are first-class state-inference problems, and they're capacity-friendly. Excluding them is preference, not principle.
- **Replacement**: Full equity-complex action space, including pairs.
- **Principle**: DESIGN.md "Out of Scope" — pre-committed action expression.

### Equity-direction-only action space
- **Implicit in early BUILD.md**.
- **Caught by Michael**. Rejected because: volatility trades, options expressions, dispersion are well-suited to retail size and uses options data we're already pulling.
- **Replacement**: Full equity-complex action space (equity / options / vol / pairs / no-edge). Expression is chosen by the agent based on payoff structure and capacity.
- **Principle**: DESIGN.md "Operational Constraints."

---

## Role / architecture bias attempts

### Michael as baseline / training signal (the 4-quadrant matrix)
- **Proposed (by Claude)**: "Run the system in parallel to Michael's discretionary trading. Score system ↔ Michael as agreement / disagreement / over- / under-confidence. Use as a calibration diagnostic."
- **Caught by Michael's audit.** Rejected because: even framed as "just diagnostics," using Michael's calls as a comparison anchor smuggles his bias into the system's loss function. Michael is the auditor, not a calibration input.
- **Principle**: DESIGN.md #10 — Michael as auditor only. The 4-quadrant matrix is explicitly out of scope.

### Paper trading before live
- **Proposed (by Claude)**: Standard "paper trade for N months before going live."
- **Rejected because**: Michael is already trading live with his own discretion. The system doesn't need to "ramp into" real money; it needs to be honest enough that when ready, Michael switches to it. Live operation from the moment the agent is alive — scored against time-revealed labels.
- **Principle**: DESIGN.md "Operational Constraints" — no paper trading.

### DCF as architectural / physics
- **Proposed (by Michael, then debated)**: "DCF is law, like physics."
- **Rejected** (with Michael's agreement). DCF is a strong prior, often holds, frequently fails (bubbles, reflexivity, option-like equities). Real architectural physics: time value, Bayesian updating, Kelly, compound asymmetry, no-arbitrage, conservation of probability. DCF builds on top of these.
- **Principle**: DESIGN.md "Architectural Physics" — DCF is *prior*, not invariant.

### Pre-defined hypothesis space / state ontology
- **Proposed (early framing)**: Define a fixed set of hidden states the agent reasons over.
- **Rejected because**: pre-defined ontology bottlenecks search. Models should propose their own hypothesis spaces; evaluator filters.
- **Principle**: DESIGN.md "The Six Layers" — Layer 2 hypothesis space is *open*.

### Pre-engineered features as primary model input
- **Proposed (early framing)**: Hand-engineer features (sales-cycle-elongation-delta, etc.) and feed them to the model.
- **Rejected because**: bottlenecks the model interface. Model should see raw evidence and decide what to attend to.
- **Principle**: DESIGN.md #6 — model reasons natively over raw evidence.

### Single-agent architecture
- **Proposed (early framing)**: One agent + memory + skills.
- **Rejected because**: locks the system into one cognitive style and one model. Population is the unit of search.
- **Replacement**: Population of agents varying in (model × memory × prompt × reasoning approach).
- **Principle**: DESIGN.md #9.

---

## Memory architecture deliberations

### Memory architecture v1 (2026-05) — committed to lean MVP

- **Context**: substantive evaluation of 2026 LLM-agent-memory research (Kumiho graph-native belief revision, SSGM governance middleware, MemMachine ground-truth-preserving, Tencent four-tier pyramid, GBrain self-wiring knowledge graph, Claude Code two-tier auto-memory, Hermes, Codex thread-scoped DB, Sakana doc-to-LoRA, AtomicStrata wiki-compiler, Yegge/Tan thin-harness-fat-skills, ArcticDB hedge-fund research database) before committing to substep 7 (memory schema design).
- **Decision**: Lean MVP — four-tier semantic pyramid (L0 Trajectory / L1 Observation / L2 Probationary Hypothesis / L3 Promoted Skill), git-backed YAML at L2/L3 with two edge types (`derived_from`, `supersedes`), four-check promotion gate (existing DESIGN.md), L0/L1 in Postgres tables, code-level boundary enforcement (`src/fingym/agents/` cannot import from `src/fingym/evaluator/`).
- **Deferred (with revisit triggers)**: NLI contradiction check at promotion, `depends_on` and `contradicts` edges, reversible-reconciliation cron, continuous per-use confidence scoring, capped index file, Postgres edge index, skill-as-markdown procedures, read-only vector retrieval over L0. Each item carries an explicit trigger in [memory-design.md](memory-design.md) deferral table.
- **Rejected outright**: vector retrieval over agent-writable stores (FMP defense, DESIGN.md #6); Neo4j or other graph DB (overkill at our scale); Sakana hypernetwork parametric memory (auditability over speed); flat append-only memory (UMG); recency-only eviction; agno ops platform at MVP; wiki-compiled corpus as primary input (would violate DESIGN.md #6 — runs as Phase 1 A/B experiment instead).
- **Principle**: DESIGN.md #4 (verified updates), #5 (cognition/verification boundary), #6 (raw evidence), #7 (model-agnostic memory), plus the project's "no scaffolding" and BIAS_PATTERNS #10 (scope expansion without reason) — build the smallest architecture that honors DESIGN.md, add complexity only when triggered.
- **Authoritative spec**: [memory-design.md](memory-design.md). This DECISIONS.md entry is the audit record; memory-design.md is the architecture document.

---

## Constitution tightening v1 (2026-05)

- **Context**: Michael's review during the pre-substep-4 design pass identified language drift risks and one concrete drift risk in the data-spine schema. The review framing — *"the verifier may encode physics, not alpha"* — sharpened the cognition/verification boundary in a way the original DESIGN.md language did not. Three concrete tightenings landed simultaneously, before the evaluator v0 build, on the principle that we are in the "getting it right" phase, not the "minimize previous work" phase.

- **Decision** (three coordinated changes):
  1. **Physics-not-alpha sharpening of DESIGN.md commitment #5.** Added a clarifying block-quote: "The verifier may encode physics — Bayes, Kelly, proper scoring, point-in-time discipline. The verifier may not encode alpha. Hand-coded rules in the verification layer are physics. Hand-coded rules in the cognition layer are alpha smuggling. The distinction is load-bearing: 'no hand-coded rules' is wrong (the verifier IS hand-coded rules); 'no hand-coded alpha cognition' is right." The matching sentence in CLAUDE.md "The Goal" was updated from "No hand-coded rules" to "No hand-coded alpha cognition."
  2. **`derived_features` → `derived_evidence` rename + scope language.** DESIGN.md Layer 0, TECHNICAL.md schema list, PYRAMID.md Stone 23, and `src/fingym/data/__init__.py` docstring all updated. New scope paragraph in DESIGN.md Layer 0 defines derived evidence as mechanically generated, fully provenance-linked transformations of raw emissions (speaker-turn extraction, section-tagging, peer-group construction, return aggregation) — never alpha logic, scoring, ranking, or signal. The `derived_evidence` Postgres table is **not created at Phase 0**; the constitutional slot exists, the table arrives with a need.
  3. **Trajectory-as-audit-object clarification + new BIAS_PATTERNS entry #11 "narrative-as-evidence."** DESIGN.md Layer 5 now states explicitly that the audit object of record is the structured trajectory `(evidence_t → belief_t → action_t → label_{t+k} → score_{t+k})`; prose rationales are a secondary inspection surface only. CLAUDE.md updated from "Ten specific patterns" to "Eleven specific patterns" with narrative-as-evidence added to the named list.

- **Mechanism added**: `mechanisms/lints/no_alpha_features.py` — strict denylist of historical quant-alpha compound names (`quality_score`, `value_premium`, `momentum_factor`, `tone_score`, `founder_premium`, `conviction_rank`, etc.; 25 entries). Scans `src/fingym/` and `migrations/`; skips `evaluator/`, `toys/`, `tests/`, `mechanisms/`. Per-line override marker `# derived-evidence-allow: <reason>` for legitimate mechanical transformations that happen to include a denylisted token. 22 unit tests in `tests/unit/test_no_alpha_features.py`. Wired into `.pre-commit-config.yaml`. The lint is a tripwire, not airtight — extending the denylist requires a DECISIONS.md entry; weakening it requires a DECISIONS.md entry plus Michael sign-off.

- **Pushbacks recorded** (claims Claude argued against in the review and Michael accepted):
  - Adding "2-month" explicitly to the multi-horizon list was rejected as the wrong abstraction; the architectural commitment is *evaluator parameterizable on horizons*, not a longer fixed list. To be enforced when the evaluator is built (substep 4).
  - Building 8 proposed lints up front was rejected as mechanism-bloat; only `no_alpha_features.py` lands now. `time_leak_guard` and `promotion_requires_holdout` are queued for Phase 1 / Phase 4 respectively. The remaining proposals (`raw_evidence_required`, `output_schema_required`, `no_fixed_hypothesis_ontology`, `no_prompted_checklist_lock`, `no_human_label_import`) are addressed by the type system, the Protocol contract, or import-linter — not by additional lints.
  - "Prose rationales are zero-value" was rejected; the right framing is *trajectory is the audit object of record; prose is a secondary inspection surface for catching bias smuggling and narrative drift.* Reflected in the DESIGN.md Layer 5 paragraph.

- **What does NOT change**: The 10 commitments. Phase 0 next action (substep 4: evaluator v0 + 3-state synthetic toy). The teaching cadence. The repo structure. The two existing lints. The pyramid stones taught so far.

- **Files touched**: CLAUDE.md, DESIGN.md, TECHNICAL.md, PYRAMID.md, BIAS_PATTERNS.md, `src/fingym/data/__init__.py`, `mechanisms/lints/no_alpha_features.py` (new), `tests/unit/test_no_alpha_features.py` (new), `.pre-commit-config.yaml`, this file. Pre-commit suite green across 15 hooks; 22/22 lint tests green.

- **Principle**: DESIGN.md #5/#6 (cognition/verification boundary), Layer 0 (data spine integrity), Layer 5 (audit object); plus the project's "mechanisms over prompts" — the language tightening would have been load-bearing prose without the matching lint. The lint is what makes the language enforceable.

---

## Constitution tightening v2 (2026-05)

- **Context**: Following Michael's second design synthesis (the "AI cognition + EdgeContract" review), five concrete tightenings landed before substep 4 (evaluator v0). The synthesis's central insight — *"no cognitive output matters unless it becomes a structured, point-in-time, market-relative, economically expressible, future-scored contract"* — is the bridge from "AI thinks freely" to "we make money." That bridge is the structured terminal output object. We are still in the design-before-build phase; tightenings here cost less than tightenings after code lands. Claude's prior recommendation to defer most items to phase-gate was over-applied — for pure-design changes there is no data to wait for. Recalibrated to land all design-pure items now; only the VOI computation mechanism stays deferred (the data-capture requirement lands now).

- **Decision** (five coordinated changes):
  1. **Four-thing decomposition vocabulary.** Added `S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)` as load-bearing vocabulary. Lives canonically in [DEFINITIONS.md](DEFINITIONS.md); DESIGN.md "Architectural Physics" introduces the decomposition in a table and the load-bearing claim that money lives in the gap between `P_AI(S)` and `P_market(S)` only when `Action(A)` monetizes the disagreement after costs.
  2. **DESIGN.md commitment #2 sharpened.** Extended "Belief is over hidden state" with the price-as-adversarial-belief framing: the agent infers state AND infers what the market believes about state; the system monetizes the gap, not the absolute belief. A perfectly calibrated belief that the market also holds produces no edge.
  3. **NO-EDGE elevated to a DESIGN.md Operational Constraint.** Previously a BUILD.md mention. Now structurally first-class: the verifier explicitly rewards `NoAction` calls when no expression has positive expected log-growth-after-costs. An agent whose no-edge rate is implausibly low is flagged (BIAS_PATTERNS.md #12). The contract format treats `NoAction` as a typed alternative to `TradeAction`, not a degenerate case.
  4. **CONTRACT.md created** ([CONTRACT.md](CONTRACT.md)). MVP spec for the structured terminal output every agent emits. Required fields buildable at Phase 0 substep 6: `decision_time`, `evidence_ids`, `hidden_state_hypotheses`, `ai_belief`, `market_implied_belief`, `belief_delta`, `horizon`, `action_or_no_action`, `recommended_size`, `falsifiers`, `label_plan`, `cognitive_audit_trail`, `memory_update_proposal`. Deferred fields (cost_model, slippage_model, payoff_distribution, capacity_estimate, etc.) listed with explicit Phase triggers. Same MVP-then-defer pattern as memory-design.md.
  5. **PYRAMID.md Stone 11a + Stone 19 sharpening + BIAS_PATTERNS #12.** New Stone 11a in Layer 2: market-delta scoring (the agent's belief minus market-implied belief, scored against realized payoff). Without it the scoreboard cannot distinguish "well-calibrated but no edge" from "well-calibrated AND edge." Stone 19 (model interface contract) sharpened to point at CONTRACT.md and list required vs deferred fields. New BIAS_PATTERNS #12 "trade-for-trade's-sake" — the failure mode of an agent that always proposes a trade rather than declaring no-edge.

- **Naming convention adopted**: Stone IDs are permanent and never renumbered. Insertions get letter suffixes (Stone 11a, etc.). This avoids cascading reference breakage when stones are added — the v1 DECISIONS.md entry that references "PYRAMID.md Stone 23" stays valid.

- **VOI for compute — split decision**: The data-capture requirement (`cognitive_audit_trail` field on every Contract, with one entry per cognitive iteration) lands NOW as a required field of CONTRACT.md, because the trajectory store needs to start capturing the trail from day 1 for Phase 4 to have data to consume. The mechanism that COMPUTES VOI from the trail (per-agent cost vs decision-changes analysis) is genuinely Phase 4 work and stays deferred — it requires the population mechanic and per-agent cost data, neither of which exists at Phase 0.

- **Pushbacks recorded** (claims Claude argued against in the v2 review and Michael accepted):
  - Adopting the synthesis's 11-numbered-step prompt skeleton was rejected as BIAS_PATTERNS #8 (narrowing the model interface). The contract object IS the constraint; the model decides its own internal reasoning sequence.
  - Adopting the synthesis's 7-stage funnel as a model-side workflow was rejected for the same reason. The funnel is reframed as system-side gates (validate → score → promote), not as model-side reasoning steps.
  - Creating a separate `COGNITION_AND_VERIFICATION_DOCTRINE.md` doc was rejected as source-of-truth fragmentation. The substantive claims from the synthesis's 10 doctrine principles are absorbed into existing docs (DESIGN.md, CONTRACT.md, BIAS_PATTERNS.md) rather than spawning a fourth source-of-truth.
  - Building the synthesis's full EdgeContract schema (with cost models, slippage models, capacity, payoff distributions baked in NOW) was rejected as over-engineering at Phase 0. The MVP CONTRACT.md spec covers the Phase 0 evaluator's needs; advanced fields are listed as deferred with explicit triggers.

- **Pushback Claude made initially and reversed**: Claude initially recommended deferring most v2 items to the substep-8 phase-gate audit on the grounds that "doing v2 immediately makes the constitution look unstable." Michael correctly pointed out this conflated optics with substance — for pure-design changes that are cheaper to land before build than after, the deferral discipline was over-applied. Recalibrated.

- **What does NOT change**: The 10 commitments. Phase 0 next action (substep 4: evaluator v0 + 3-state synthetic-market toy). The teaching cadence (concept-in-PYRAMID-then-code). The repo structure. The mechanism layer (no new lints in v2).

- **Files touched**: CLAUDE.md, DESIGN.md, TECHNICAL.md, DEFINITIONS.md, PYRAMID.md, BIAS_PATTERNS.md, CONTRACT.md (new), this file, PROGRESS.md.

- **Mechanism additions**: None. The v1 lint (`no_alpha_features.py`) plus the existing two cover what's structurally enforceable. The contract spec is enforced by the type system once `src/fingym/agents/contract.py` ships in substep 6. The four-thing decomposition is vocabulary; it doesn't admit a clean lint pattern. Trade-for-trade's-sake (BIAS_PATTERNS #12) is detected at the scoreboard, not at the lint layer.

- **Principle**: DESIGN.md #2 (belief over hidden state, sharpened), #5 (cognition / verification boundary at the contract object), #6 (raw evidence in, structured contract out), Operational Constraints (NO-EDGE first-class). Plus the project's "mechanisms over prompts" — the contract spec without code enforcement (the pydantic model in substep 6) is load-bearing prose; the spec PLUS the validator is enforceable.

- **Forward implications for substep 4 (evaluator v0)**:
  - The evaluator must support multi-horizon scoring on a parameterizable horizon set (not hardcoded), with market-delta scoring (Stone 11a) as a column on the scoreboard.
  - The 3-state synthetic-market toy (Stone 15) must include a market participant with its own belief, so the evaluator can score `belief_delta` in toy world.
  - The evaluator must score `NoAction` calls separately from `TradeAction` calls (not collapse them to size = 0).

---

## Disposition guidance

When a new session encounters a proposal that matches anything in this file:

1. **Recognize the pattern.** Look up the proposed item in this log.
2. **Refuse without re-litigating.** The rejection is documented. State which entry applies.
3. **Surface to Michael only if new evidence has emerged** that materially changes the rejection rationale. Otherwise, do not consume Michael's bandwidth re-evaluating settled questions.

The opposite failure mode — adding things to this list that weren't actually rejected — is also forbidden. New rejections require either a documented Michael decision or an explicit DESIGN.md principle violation.
