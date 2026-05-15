# FinInferenceGym — Design

The locked-in architectural constitution. Principles in this document do not change with execution choices. If a build step would violate any commitment here, the build step changes, not the commitment.

When this document conflicts with anything else, this wins. When evidence demands a change here, the change is explicit, deliberated, and logged.

Operational specifics, phasing, and build steps live in [BUILD.md](BUILD.md). Vocabulary lives in [DEFINITIONS.md](DEFINITIONS.md). Foundational intuitions live in [intuitions.md](intuitions.md). Project operating manual lives in [AGENTS.md](AGENTS.md).

---

## Purpose

A system that absorbs frontier AI improvements to generate calibrated, verifiable alpha in equity markets through hidden-state inference, market-implied belief recovery, and rigorous evaluator-driven self-improvement.

## Goal

Maximize absolute compound growth (log-wealth) of deployed capital by:

1. Forming calibrated beliefs about hidden state for each company in the operating universe.
2. Recovering the market's implied belief about the same hidden state.
3. Acting on calibrated disagreements where the gap clears costs, slippage, and capacity constraints.
4. Continuously improving the system on verified evidence — never on narrative, confidence, or unverified intuition.

**Not maximizing**: Sharpe, equity-curve smoothness, low drawdown, volatility-of-good-returns. These are deliberately deprioritized.

---

## First-Principles Commitments

Non-negotiable. Every architectural choice is downstream of these. If any one is violated, the architecture is broken.

### 1. The evaluator is the load-bearing primitive.
Not the model. Not the strategy. Everything else is replaceable; the evaluator is not.

### 2. Belief is over hidden state, not over outcomes.
The agent infers state; the evaluator scores against time-revealed labels.

### 3. Time is a one-way valve.
Point-in-time discipline is absolute. Information flows forward to the evaluator, never backward to the agent.

### 4. Verified updates only.
Skills, features, hypothesis spaces, memory items — anything that changes agent behavior must survive held-out replay before promotion.

### 5. The cognition / verification boundary is absolute and one-way.
The model is the cognitive engine. The system is the verifier.

> **Cognition stays in the model. Rigor stays in the system. They do not overlap.**

> **The verifier may encode physics — Bayes, Kelly, proper scoring, point-in-time discipline. The verifier may not encode alpha.** Hand-coded rules in the verification layer are physics. Hand-coded rules in the cognition layer are alpha smuggling. The distinction is load-bearing: "no hand-coded rules" is wrong (the verifier IS hand-coded rules); "no hand-coded alpha cognition" is right.

The model is granted **maximum** freedom to reason. The evaluator applies **maximum** strictness to its outputs. **Every constraint that would narrow the model's search space must migrate to the verification side, never sit on the cognition side.** The agent never judges itself.

### 6. The model reasons natively over raw evidence.
No pre-engineered features as primary model input. No templated reasoning paths. No fixed hypothesis ontologies.

> **The system extracts the maximum native intelligence of whatever model it has access to.**

Bottlenecks at the model interface destroy the ride-the-exponent property and are not permitted. Terminal outputs are structured (so the evaluator can score them). The reasoning that produces them is free.

### 7. Intelligence lives in architecture, not in weights or prompts.
Models are swappable engines. Memory, hypothesis registry, evaluator, and promotion gate are all model-agnostic. The system is not "a model doing investing." It is an architecture that uses models as interchangeable cognitive components.

### 8. Two-axis improvement is architectural, not aspirational.
The system improves on **the model axis** (frontier swap, open-weights swap) AND **the data axis** (accumulated verified trajectories → fine-tuned own-model). Both paths are designed in from day 1.

> **The year-2 own-model fine-tune is a planned trajectory, not a hedge.**

SFT, continued pre-training, and post-training on verified trajectories are explicit architectural commitments. The data spine is built from day 1 to produce trajectory data fit for these.

### 9. Population, not single agent.
Multiple agents run in parallel, varying in (model × memory subset × prompt structure × reasoning approach). Selection is by evaluator scoreboard. **There is no single-agent commitment that locks the system into one cognitive style or one model.** The population is the unit of search.

### 10. Michael is the auditor of the auditing system.
Not a calibration input. Not a training signal. Not a baseline.

> **The "system ↔ Michael agreement / disagreement / overconfidence" comparison pattern is explicitly rejected.**

Even framed as "diagnostics," using Michael's discretionary calls as a comparison anchor smuggles his bias into the system's loss function. His discretionary trading is unrelated to the system's evaluation. The system is graded by time-revealed labels only.

---

## Architectural Physics

The mathematical/structural constants the system cannot deviate from.

- **Time value.** A dollar now ≠ a dollar later.
- **Bayesian updating.** Belief change is forced by `prior × likelihood ÷ sum`. No learning rate; the math is mechanical.
- **Kelly criterion.** Long-run compound growth is maximized by sizing proportional to edge, scaled inversely by outcome variance.
- **Compound asymmetry.** A drawdown of D requires a gain of `D/(1−D)` to recover. 100% loss is unrecoverable.
- **No-arbitrage at the margin.** Risk-free arbitrage opportunities are converged on by other participants.
- **Conservation of probability.** Beliefs sum to 1. No belief is exactly 0 or 1 unless logically certain (Cromwell's rule).

DCF, fundamental valuation, and other classical finance frameworks are **strong priors**, not architecture. They often hold and frequently fail. The system uses them where they apply and discovers when they don't.

---

## Searchable vs Architectural

| Architectural (does not change) | Searchable (evolves under selection) |
|---|---|
| Bayesian update math | Likelihood specifications |
| Kelly sizing math | Edge models |
| Proper scoring rules (Brier, log score) | Hypothesis spaces (what states are entertained) |
| Calibration principle | Source diets |
| Held-out promotion gate | Skills / memory items |
| Time-revealed label structure | Decision rules / action policies |
| Point-in-time discipline | Universe (within operational criteria) |
| Audit by Michael | Specific agents in the population |
| Six data types + provenance | Model used for cognition |
| **Cognition / verification non-overlap** | Population size and composition |
| **Raw-evidence model interface** | Prompt structures and reasoning approaches |
| **Population as the unit of search** | Memory contents |
| **Two-axis improvement (model + data)** | Frontier model choice |
| **Model-agnostic memory format** | Open-weights vs frontier selection |

Architectural commitments are encoded in code that the system cannot self-modify. Searchable elements are versioned artifacts that change through verified promotion.

---

## The Six Layers

Lower layers must be calibrated before higher layers depend on them.

### Layer 0 — Data Spine
Immutable, point-in-time, versioned. All data flows through this layer. Six data types: **raw emissions**, **derived evidence**, **beliefs**, **actions**, **labels**, **scores**. Every record carries timestamp + provenance + version. Live feed and historical replay are structurally identical pipelines.

> **Derived evidence is mechanically generated, fully provenance-linked, inspectable transformations of raw emissions** — speaker-turn extraction from a transcript, section-tagging of a 10-K, peer-group construction by SIC code, return aggregation from prices. It is reproducible from the raw emission plus the version of the transformation code. **It is not alpha logic, scoring, ranking, or signal.** Anything labeled "score," "rank," "premium," "factor," "signal," or "quality" is not derived evidence — it is alpha cognition and belongs in the model, not in the spine. The naming is enforced by `mechanisms/lints/no_alpha_features.py`.

The data spine is also the trajectory store — every belief / action / outcome / score is preserved with full provenance, in a format fit for eventual fine-tuning of own-models.

### Layer 1 — Evaluator
Scoreboard, not single scalar. Scores beliefs and actions against time-revealed labels using proper scoring rules. Tracks: calibration (Brier, log score), process quality (Bayesian-update vs price-chasing detection), decision-changing information per dollar (cost-aware VoI), edge at deployable size (impact-adjusted), compound growth + drawdown discipline (Kelly-objective), out-of-sample stability (holdout / regime / sector / time splits).

### Layer 2 — Hypothesis Space (Open)
Not pre-defined. Models propose state structures, likelihood specifications, and causal hypotheses. The system stores and tests any proposal that survives the evaluator. The space is bounded only by what survives verification, not by a fixed ontology.

### Layer 3 — Model Interface (Swappable, Free)
The cognitive engine.

The model receives **raw evidence** — full transcripts, full options chains, multi-quarter histories, peer data, macro context. **No pre-engineered features as primary input.** The model is allowed full freedom to reason, form hypotheses, define state structures, plan research, search counterfactuals, propose memory updates.

**Reasoning is free; terminal output is structured.** The terminal output is a typed object — belief over state + recommended action + sizing + uncertainty + proposed memory updates — that the evaluator can score.

The model is **swappable**: frontier API, open-weights, eventually fine-tuned own-model. The model interface is the same regardless of which model is plugged in.

### Layer 4 — Memory + Population + Promotion
Memory is versioned, model-readable artifacts: skills, hypotheses, observations, lessons. Stored as versioned files; any model can read and propose modifications. Memory is model-agnostic in format — text and structured data, not embeddings or model-specific representations.

**The system runs a population of agents**, not a single agent. Each agent is a (model × memory subset × prompt structure × reasoning approach) tuple. The population varies along all four dimensions. Agents compete on the evaluator scoreboard. Selection is by survival of calibrated performance under out-of-sample replay.

Promotion gate: any memory addition or population change must survive held-out replay + live calibration check + cross-model regression. Memory outlives any one model — this is how knowledge compounds across model generations and how the system rides the data axis of improvement.

### Layer 5 — Audit (Michael)
Reviews evaluator integrity, prior reasonableness, data discipline, and promotion-log honesty. Approves architectural changes. Catches smuggled biases. Maintains the standing audit questions (below).

> **The audit object of record is the structured trajectory:** `(evidence_t → belief_t → action_t → label_{t+k} → score_{t+k})`. Prose rationales from the model are a **secondary inspection surface** — useful for catching specific failure modes (bias smuggling, narrative drift), but they cannot substitute for the trajectory. A model producing eloquent rationales with poor calibration scores low; a model producing sparse rationales with excellent calibration scores high. **Beautiful narrative ≠ inference quality.** See BIAS_PATTERNS.md #11 (narrative as evidence).

---

## Ride-the-Exponent Principle

The system improves on two independent and complementary axes. **Both are architectural, not aspirational.** A system on both axes outperforms a system on either alone, and continues compounding as models and data both grow.

### Model axis
As models get better, the system gets better automatically. This is possible only because:
- The model interface is open (raw evidence in, free reasoning, structured terminal output).
- The system extracts **maximum native intelligence** from whatever model is plugged in — no narrow tasks, no templated prompts, no pre-engineered features as primary input.
- Swap infrastructure exists from day 1; model choice is searchable.

> A system that uses 5% of a frontier model's capability will be beaten by a system that uses 100% of a weaker model. Both will be beaten by a system that uses 100% of a frontier model. We design for the latter.

### Data axis
Verified trajectories accumulate from day 1. Every belief, action, outcome, and score is stored in the data spine with full provenance, in trajectory format. By year 2 this trajectory store becomes:

- **SFT data** for fine-tuning an open-weights model into a specialist agent.
- Possibly the basis for **continued pre-training** or **post-training** on the domain.
- A structural defense against frontier API restriction or model gating (already happening).

> The own-model path is a planned trajectory, not a fallback. It is the substrate that protects the system as frontier access narrows.

### The compounding
The two axes interact. A better model fine-tuned on better data outperforms either alone. The population mechanic means we can run both kinds of agents in parallel — frontier-API agents AND own-fine-tuned agents — and let the evaluator select between them.

---

## Operational Constraints

Rules for how we operate inside the architecture.

- **Universe is broad by default.** The analytical universe is as wide as available data + operational/structural criteria allow — likely thousands of US equities. The active-capital universe (where capital deploys) is bounded only by where calibrated edge × capacity × Kelly justifies action. A learning/toy universe (~30 names) is used to validate the evaluator and agent pipeline against ground truth; it is *not* the production universe. **Narrowing the production universe out of preference rather than structural necessity is bias-import.**
- **Multi-horizon scoring.** Every belief is scored against labels at multiple horizons in parallel — 1 month, 3 months, 6 months, 1 year (toys may use shorter horizons for fast iteration). The system discovers empirically at which horizon each agent has edge. The system never pre-commits to a single horizon.
- **Full equity-complex action space.** Operational action space includes long/short equity, options (calls, puts, spreads, straddles, strangles, calendar), volatility trades (long vol, short vol, dispersion, vol-calendar), and pairs / relative-value within the same complex. The agent's terminal output includes belief + recommended expression + sizing + horizon-of-edge. Expression is chosen for asymmetric payoff capture and capacity, not for stylistic preference.
- **Universe selection by operational and structural criteria only.** Data availability, emission richness, PIT depth, liquidity, options availability. Never by sector, theme, story, or thematic view. Themes are *outputs* of the system, never inputs.
- **Time-revealed labels are the only ground truth.** No human-labeled training data. No "Michael says this is right."
- **No paper trading.** Live performance scored against time-revealed labels. The market is the production environment.
- **Michael is the auditor, not the training signal.** His discretionary trading is unrelated to the system's evaluation. The 4-quadrant comparison matrix (agreement / disagreement / over- under-confidence relative to Michael) is rejected.
- **No bias-import.** Every constraint introduced into the architecture must be defensible from first principles or explicitly logged as a working assumption to be retested.

### Structural exclusions (not preferences)

These are out of scope because the playing field is structurally uneven for a single operator, not because they aren't valuable in principle:

- **HFT, market-making, intraday order-book strategies.** Require co-location, specialized infrastructure, and capital structure unavailable to a single retail operator.
- **Cross-asset (bonds, FX, commodities, macro).** Different expertise and data spine; out of scope for retail US-equity focus.
- **Private markets.** Not retail-accessible at meaningful size.

If structural conditions change (e.g., the operator scales meaningfully), these can be revisited.

---

## Out of Scope

Explicitly rejected:

- **Sharpe optimization** as a target. Log-wealth is the objective.
- **Narrative scoring** ("does this insight sound reasonable"). Only time-revealed labels score.
- **Pre-engineered features as primary model input.** The model sees raw evidence.
- **Embedded thematic priors** (e.g., "AI dispersion will be huge" baked into universe selection or hypothesis space). Themes are outputs, not inputs.
- **Human-in-the-loop training signals.** No human labels target training.
- **The "system ↔ Michael agreement / disagreement / over- under-confidence matrix" as a diagnostic.** Even framed as "just diagnostics," using Michael's discretionary calls as a comparison anchor smuggles his bias into the system's loss function.
- **Insider information / material non-public information** from inside sources. Public alt-data emissions are in scope; material non-public is not.
- **Closed-box end-to-end systems.** Every layer must be inspectable.
- **Bottlenecking the model interface.** Narrow prompts, templated reasoning, fixed ontologies, or any other mechanism that prevents the model from using its full native intelligence on raw evidence is forbidden.
- **Single-agent architectures.** The system is a population. No design that locks into one cognitive style.
- **Pre-committed time horizon.** The system scores at multiple horizons in parallel. No design that locks into "we are a quarterly horizon system" or similar.
- **Pre-committed action expression.** The action space is the full equity complex. No design that locks into "we are a long-only equity system" or "we are a directional system." Expression is chosen by the agent based on payoff structure and capacity, not by architectural preference.
- **Narrowed production universe by preference.** A learning/toy universe is fine for evaluator validation. Narrowing the *production* universe out of preference (e.g., "concentrate on a few names with conviction") rather than structural necessity is bias-import.

---

## Audit Principle

Michael's standing audit questions:

1. **Is the evaluator measuring inference quality or luck?**
2. **Are the priors and hypothesis space sane?** (Cromwell sweeps.)
3. **Is data discipline holding?** Restatement leaks? Look-ahead leaks? Live-feed parity?
4. **Are skill promotions calibrated?** Look at both promoted and rejected. Under- or over-promoting?
5. **Have we added a constraint disguised as "obviously X"?** Every "obviously" is a candidate for narrowing the search space and should be challenged.
6. **Has anything migrated *out* of verification and *into* cognition?** Constraints in the wrong layer are the single most common silent failure.
7. **Is the model interface still open?** Have we accidentally narrowed what the model sees or how it can reason?

**When system output confirms a story Michael already holds, the bar rises, not falls.** Confirmation is the hardest thing to evaluate honestly.

---

## Failure Modes & Mitigations

| Failure mode | Mitigation |
|---|---|
| Overconfident beliefs producing bankroll-destroying bets | Fractional Kelly absorbs miscalibration of edge and time |
| Pattern-matching emissions as if they were state | "Update on emissions, not on price"; process metrics distinguish |
| Confidently wrong about a state outside the hypothesis space | Cromwell's rule; periodic hypothesis-space audits |
| Promoted skills overfit on historical replay | Multi-split holdout (regime, sector, time, cross-model) |
| Evaluator becomes the target (Goodhart) | Scoreboard not scalar; promotion uses vector, not single number |
| Regime change invalidates calibration | Process metrics + drift detectors; periodic re-validation across regimes |
| Reflexivity at production size | Capacity-adjusted scoring; deployable edge ≠ nominal edge |
| Model lock-in | Model swap test in week 12; year-2 fine-tune plan; population mechanic |
| Narrative drift | Time-revealed labels are the only ground truth |
| Bias-import from Michael's views | Audit principle (#5–#7); explicit rejection of comparison matrix |
| Bottleneck migration into cognition layer | Audit principle (#6); raw-evidence interface; structured outputs only at terminal |
| Survivorship bias in evidence corpus | Delisted shadow universe (PIT fundamentals + prices for delisted names) used in every promotion check involving corpora known to be survivor-biased |

---

## Year-1 vs Year-2 Outlook

**Year 1** (12 weeks of intensive build, then live operation):
- All six layers operational.
- Population of frontier-API-driven agents running live.
- Memory accumulating via verified promotion.
- Model-swap test passed.
- Trajectory store accumulating in SFT-fit format.
- Measurable edge vs market baseline on at least one decision class.

**Year 2**:
- Open-weights model fine-tuned (SFT, possibly post-training) on accumulated verified trajectories. Tested as a population member.
- Universe expansion as calibration holds.
- Capacity-aware scaling.
- If circumstances warrant: own-model training as primary or secondary engine; reduced dependence on frontier API access.

---

## Change Control

This document changes only when:

1. Evidence demonstrates a principle is wrong.
2. The audit (Layer 5) flags a violation requiring reformulation.
3. A new commitment is added that has been explicitly deliberated.

Routine implementation choices do not change DESIGN.md. They live in BUILD.md.
