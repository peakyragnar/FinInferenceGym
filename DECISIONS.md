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

## Disposition guidance

When a new session encounters a proposal that matches anything in this file:

1. **Recognize the pattern.** Look up the proposed item in this log.
2. **Refuse without re-litigating.** The rejection is documented. State which entry applies.
3. **Surface to Michael only if new evidence has emerged** that materially changes the rejection rationale. Otherwise, do not consume Michael's bandwidth re-evaluating settled questions.

The opposite failure mode — adding things to this list that weren't actually rejected — is also forbidden. New rejections require either a documented Michael decision or an explicit DESIGN.md principle violation.
