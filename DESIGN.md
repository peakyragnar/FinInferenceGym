# FinInferenceGym — Design

The locked-in architectural constitution. Principles in this document do not change with execution choices. If a build step would violate any commitment here, the build step changes, not the commitment.

When this document conflicts with anything else, this wins. When evidence demands a change here, the change is explicit, deliberated, and logged.

Operational specifics, phasing, and build steps live in [BUILD.md](BUILD.md). Vocabulary lives in [DEFINITIONS.md](DEFINITIONS.md). Foundational intuitions live in [intuitions.md](intuitions.md). Project operating manual lives in [AGENTS.md](AGENTS.md).

---

## Purpose

> FinInferenceGym is a contract-scored, point-in-time replay engine for evolving financial belief systems.

A system that absorbs frontier AI improvements to generate calibrated, verifiable alpha in equity markets through native agent forecasting of realized returns, empirical per-signal-class calibration via the Forecast Ledger, and rigorous evaluator-driven self-improvement.

## Goal

Maximize absolute compound growth (log-wealth) of deployed capital by:

1. Forming forecast distributions over realized returns for each `(name, horizon, expression-type)` the agent operates over.
2. Calibrating those forecasts empirically against a per-signal-class Forecast Ledger that tracks realized-vs-claimed reliability over many forecasts.
3. Acting only when calibrated expected utility, after costs and slippage, clears a margin-of-safety threshold. The Market-State Baseline (Track C) runs in isolation as a control and attribution layer — never as an input to the action gate.
4. Continuously improving the system on verified evidence — never on narrative, confidence, or unverified intuition.

**Not maximizing**: Sharpe, equity-curve smoothness, low drawdown, volatility-of-good-returns. These are deliberately deprioritized.

---

## First-Principles Commitments

Non-negotiable. Every architectural choice is downstream of these. If any one is violated, the architecture is broken.

### 1. The evaluator is the load-bearing primitive.
Not the model. Not the strategy. Everything else is replaceable; the evaluator is not.

### 2. Belief is a forecast distribution over realized returns, calibrated empirically.
The agent forecasts realized returns over `(name, horizon, expression-type)`; the evaluator scores those forecasts against the realized returns themselves. **Calibration is empirical, not assumed.** A per-signal-class Forecast Ledger tracks the agent's stated-confidence vs realized-outcome rate over many prior forecasts; reliability is a measured property of each signal class, not an a-priori model of what the market believes. The Tradable-Edge Action Engine shrinks the agent's raw forecast toward this empirical reliability and converts the result to calibrated expected utility under Kelly; action proceeds only when calibrated expected utility clears a margin-of-safety threshold that absorbs costs, slippage, and capacity. The Market-State Baseline (Track C) is a structurally isolated control — runs only on headline observable inputs (rates, vol, FX, commodities) — that produces attribution columns measuring incremental AI edge over what the headline observables alone would have produced. **The agent never sees the Baseline's processed forecast**; it sees only the same raw observables the Baseline consumes. Code-level isolation (`src/fingym/agents/` cannot import from `src/fingym/baseline/`) makes this structural, not aspirational.

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

Even framed as "diagnostics," using Michael's discretionary calls as a comparison anchor smuggles his bias into the system's loss function. His discretionary trading is unrelated to the system's evaluation. The system is graded by realized returns only.

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

### The three primitives, plus the audit layer

Every decision in the system separates three primitives (formal definitions in [DEFINITIONS.md](DEFINITIONS.md)):

| Symbol | What it is |
|---|---|
| `R_realized` | The realized return for the `(name, horizon, expression-type)`. Revealed at the horizon; not known at decision time. |
| `F_AI(R)` | The agent's forecast distribution over `R_realized`, given evidence available at decision time. Sums to 1; never assigns 0 to a value in the support (Cromwell). |
| `Action(A)` | The chosen action. Typed sum: `TradeAction | NoAction`. |

The agent's raw forecast `F_AI` is shrunk toward its **per-signal-class empirical reliability** (from the Forecast Ledger, computed over many prior forecasts) to produce `F_AI_calibrated`. Action is gated on **calibrated expected utility** (the Kelly-equivalent under `F_AI_calibrated`) clearing a **margin-of-safety threshold** that absorbs costs, slippage, and capacity. **A raw forecast alone is worthless. An empirically calibrated forecast that fails to clear the margin-of-safety threshold is also worthless.** The full chain — raw forecast, empirical calibration, calibrated expected utility, margin-of-safety gate, monetizable action — is what makes this project distinct from a calibration academic exercise.

The audit layer (separate from the action chain, visible only to the evaluator and the auditor):

| Symbol | What it is |
|---|---|
| `F_baseline(R)` | The Market-State Baseline (Track C) forecast over `R_realized`, computed only from headline observables (rates, vol, FX, commodities). Structurally isolated; the agent never sees this object. |
| `Incremental_AI_edge` | The agent's realized edge minus the Baseline's realized edge. Audit attribution column: was the edge from agent cognition, or from headline observables anyone has? |

The Baseline is an attribution control, not an action input. The agent's calibrated forecast and the Baseline's forecast are scored separately; only the agent's calibrated forecast feeds the action gate. Code-level isolation prevents the agent from optimizing against the Baseline.

---

## Searchable vs Architectural

| Architectural (does not change) | Searchable (evolves under selection) |
|---|---|
| Bayesian update math | Likelihood specifications |
| Kelly sizing math | Edge models |
| Proper scoring rules (Brier, log score) | Forecast-distribution support and shape (parametric vs nonparametric, basis choice) |
| Calibration principle | Source diets |
| Held-out promotion gate | Skills / memory items |
| Realized-return ground truth | Realized-return labelling rule (horizons, simple vs log, expression-specific payoff) |
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
Immutable, point-in-time, versioned. All data flows through this layer. Six data types: **raw emissions**, **derived evidence**, **forecasts**, **actions**, **realized returns**, **scores**. Every record carries timestamp + provenance + version. Live feed and historical replay are structurally identical pipelines.

> **Derived evidence is mechanically generated, fully provenance-linked, inspectable transformations of raw emissions** — speaker-turn extraction from a transcript, section-tagging of a 10-K, peer-group construction by SIC code, return aggregation from prices. It is reproducible from the raw emission plus the version of the transformation code. **It is not alpha logic, scoring, ranking, or signal.** Anything labeled "score," "rank," "premium," "factor," "signal," or "quality" is not derived evidence — it is alpha cognition and belongs in the model, not in the spine. The naming is enforced by `mechanisms/lints/no_alpha_features.py`.

The data spine is also the trajectory store — every forecast / action / realized return / score is preserved with full provenance, in a format fit for eventual fine-tuning of own-models. The Forecast Ledger (the per-signal-class reliability view) is computed from the `forecasts` and `realized returns` tables; it is a derived view of the data spine, not a separate store.

### Layer 1 — Evaluator
Scoreboard, not single scalar. Scores forecast distributions and actions against realized returns using proper scoring rules. Tracks: calibration (Brier, log score, reliability buckets), per-signal-class empirical reliability (the Forecast Ledger — the input to calibration shrinkage at action time), process quality (motivated-update flag), decision quality (the calibrated-expected-utility / margin-of-safety gate), edge at deployable size (capacity-adjusted), incremental AI edge over the Market-State Baseline (audit attribution), compound growth + drawdown discipline (Kelly-objective), out-of-sample stability (holdout / regime / sector / time splits).

### Layer 2 — Hypothesis Space (Open)
Not pre-defined. Models propose signal classes, forecast-distribution shapes, and causal hypotheses linking evidence to realized returns. The system stores and tests any proposal that survives the evaluator. The space is bounded only by what survives verification, not by a fixed ontology.

### Layer 3 — Model Interface (Swappable, Free)
The cognitive engine.

The model receives **raw evidence** — full transcripts, full options chains, multi-quarter histories, peer data, macro context, and the same headline observables the Market-State Baseline consumes. **No pre-engineered features as primary input.** The model is allowed full freedom to reason, form hypotheses, propose signal classes, plan research, search counterfactuals, propose memory updates.

**Reasoning is free; terminal output is structured.** The terminal output is a typed object — forecast distribution over realized returns + signal-class tag + recommended action + sizing + uncertainty + proposed memory updates — that the evaluator can score and the Forecast Ledger can calibrate.

The model is **swappable**: frontier API, open-weights, eventually fine-tuned own-model. The model interface is the same regardless of which model is plugged in.

### Layer 4 — Memory + Population + Promotion
Memory is versioned, model-readable artifacts: skills, hypotheses, observations, lessons. Stored as versioned files; any model can read and propose modifications. Memory is model-agnostic in format — text and structured data, not embeddings or model-specific representations.

**The system runs a population of agents**, not a single agent. Each agent is a (model × memory subset × prompt structure × reasoning approach) tuple. The population varies along all four dimensions. Agents compete on the evaluator scoreboard. Selection is by survival of calibrated performance under out-of-sample replay.

Promotion gate: any memory addition or population change must survive held-out replay + live calibration check + cross-model regression. Memory outlives any one model — this is how knowledge compounds across model generations and how the system rides the data axis of improvement.

### Layer 5 — Audit (Michael)
Reviews evaluator integrity, prior reasonableness, data discipline, and promotion-log honesty. Approves architectural changes. Catches smuggled biases. Maintains the standing audit questions (below).

> **The audit object of record is the structured trajectory:** `(evidence_t → F_AI_t → F_AI_calibrated_t → action_t → R_realized_{t+k} → score_{t+k})`. Prose rationales from the model are a **secondary inspection surface** — useful for catching specific failure modes (bias smuggling, narrative drift), but they cannot substitute for the trajectory. A model producing eloquent rationales with poor calibration scores low; a model producing sparse rationales with excellent calibration scores high. **Beautiful narrative ≠ inference quality.** See BIAS_PATTERNS.md #11 (narrative as evidence).

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
Verified trajectories accumulate from day 1. Every forecast, action, realized return, and score is stored in the data spine with full provenance, in trajectory format. By year 2 this trajectory store becomes:

- **SFT data** for fine-tuning an open-weights model into a specialist agent.
- Possibly the basis for **continued pre-training** or **post-training** on the domain.
- A structural defense against frontier API restriction or model gating (already happening).

> The own-model path is a planned trajectory, not a fallback. It is the substrate that protects the system as frontier access narrows.

### The compounding
The two axes interact. A better model fine-tuned on better data outperforms either alone. The population mechanic means we can run both kinds of agents in parallel — frontier-API agents AND own-fine-tuned agents — and let the evaluator select between them.

---

## The Three Arenas

The system evaluates agents across three structurally distinct arenas. Each arena has a different **epistemic status** — what it can and cannot validate. Treating them as interchangeable is a category error and a frequent failure mode.

| Arena | Scope | What it's FOR | What it CANNOT do |
|---|---|---|---|
| **Historical replay** | Finite — ~10 years × analytical universe × multiple horizons | LEARNING ground. Agents form forecasts over real evidence; skills emerge as candidates; the promotion gate filters. Grounded by real realized returns. | Past regime is not future regime. Bounded data — exhaustible in principle by aggressive search. Survivorship bias if not corrected (delisted shadow universe mitigates). |
| **Synthetic worlds** | Infinite — generate as many episodes as we want | VALIDATING THE HARNESS. Bug-catching for the evaluator, contract validator, and agent code. Stress-testing reasoning under constructed conditions. | **Cannot validate alpha.** Made-up physics; a skill that wins on a synthetic world proves nothing about real markets. Synthetic data MUST NOT enter the promotion gate as evidence — only realized returns from real data score (commitment #4). |
| **Live operation** | Slow — calendar speed, one day per day | GROUND TRUTH. Does the system actually work going forward against the market? Final examiner for any skill that survived historical replay. | Slow. Scarce. By construction; cannot be sped up. Cannot be brute-forced for discovery — used to confirm or kill, not to explore. |

The arenas work in **sequence**, not as alternatives:

1. **Synthetic** validates the harness BEFORE real data flows in (Phase 0).
2. **Historical replay** generates candidate skills against real past outcomes; the promotion gate filters (Phases 1–4).
3. **Live operation** is the final test of skills that survived historical replay (Phase 3+).

The promotion gate consumes realized returns ONLY from historical replay and live operation. **Synthetic scores never gate memory promotion.** This is non-negotiable — it is the structural defense against the most seductive failure mode: calibrating against a world we made up. See DECISIONS.md "Worldlets" for a parked future-research direction that respects this boundary.

The trajectory store accumulates Contracts from historical replay AND live operation. Year-2 own-model SFT (commitment #8) reads from this store.

---

## Operational Constraints

Rules for how we operate inside the architecture.

- **Universe is broad by default.** The analytical universe is as wide as available data + operational/structural criteria allow — likely thousands of US equities. The active-capital universe (where capital deploys) is bounded only by where calibrated edge × capacity × Kelly justifies action. A learning/toy universe (~30 names) is used to validate the evaluator and agent pipeline against ground truth; it is *not* the production universe. **Narrowing the production universe out of preference rather than structural necessity is bias-import.**
- **Multi-horizon scoring.** Every forecast is scored against realized returns at multiple horizons in parallel — 1 month, 3 months, 6 months, 1 year (toys may use shorter horizons for fast iteration). The system discovers empirically at which horizon each agent has edge. The system never pre-commits to a single horizon.
- **Full equity-complex action space.** Operational action space includes long/short equity, options (calls, puts, spreads, straddles, strangles, calendar), volatility trades (long vol, short vol, dispersion, vol-calendar), and pairs / relative-value within the same complex. The agent's terminal output includes forecast distribution + signal-class tag + recommended expression + sizing + horizon-of-edge. Expression is chosen for asymmetric payoff capture and capacity, not for stylistic preference.
- **Universe selection by operational and structural criteria only.** Data availability, emission richness, PIT depth, liquidity, options availability. Never by sector, theme, story, or thematic view. Themes are *outputs* of the system, never inputs.
- **Realized returns are the only ground truth.** No human-labeled training data. No "Michael says this is right."
- **No paper trading.** Live performance scored against realized returns. The market is the production environment.
- **Michael is the auditor, not the training signal.** His discretionary trading is unrelated to the system's evaluation. The 4-quadrant comparison matrix (agreement / disagreement / over- under-confidence relative to Michael) is rejected.
- **No bias-import.** Every constraint introduced into the architecture must be defensible from first principles or explicitly logged as a working assumption to be retested.
- **NO-EDGE is a first-class output.** A system that always finds trades is broken. The verifier explicitly rewards "no edge" calls when no expression has positive expected log-growth-after-costs. Compute should produce no-edge calls as readily as edge calls; the absence of edge is informative. An agent whose no-edge rate is implausibly low is flagged as overtrading (BIAS_PATTERNS.md #12 — trade-for-trade's-sake). The contract format treats `NoAction` as a typed alternative to `TradeAction`, not as a degenerate case.

### Structural exclusions (not preferences)

These are out of scope because the playing field is structurally uneven for a single operator, not because they aren't valuable in principle:

- **HFT, market-making, intraday order-book strategies.** Require co-location, specialized infrastructure, and capital structure unavailable to a single retail operator.
- **Cross-asset (bonds, FX, commodities, macro).** Different expertise and data spine; out of scope for retail US-equity focus.
- **Private markets.** Not retail-accessible at meaningful size.

If structural conditions change (e.g., the operator scales meaningfully), these can be revisited.

---

## Out of Scope

### What this system is NOT (purpose-level positioning)

Three system-level mischaracterizations the architecture is explicitly NOT — seductive framings that don't match what's being built:

- **"LLM reads all public information and synthesizes better than Wall Street to generate alpha."** Too weak. The model is the cognitive engine, not the system. The system is what verifies the model's output. An LLM alone does not survive the calibration discipline this architecture imposes.
- **"Invent a fake economy, train an agent in it, then trade real stocks."** Fantasy. Synthetic worlds cannot validate alpha; only time-revealed labels from real data score (#4 + Three Arenas). Skills promoted from synthetic-only evidence would be calibrating against a world we made up.
- **"Search over historical data until something works."** Data mining. The ~10-year × analytical-universe dataset is bounded; aggressive search exhausts it via overfit. The promotion gate's strictness (held-out replay + cross-model regression + survivorship check + domain-of-validity declaration) is the defense.

The architecture is none of these. The architecture-level rejections follow.

### Explicitly rejected at the architecture level:

- **Sharpe optimization** as a target. Log-wealth is the objective.
- **Narrative scoring** ("does this insight sound reasonable"). Only realized returns score.
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
| Overconfident forecasts producing bankroll-destroying bets | Calibration shrinkage toward empirical reliability; fractional Kelly absorbs residual miscalibration |
| Updating the forecast on price moves rather than on emissions | Process-quality flag distinguishes motivated from unmotivated updates; per-agent unmotivated-update-rate cap at promotion |
| Confidently wrong (near-zero probability) on a realized return that materializes | Cromwell's rule; periodic support-coverage audits; log score as smoke alarm |
| Trusting the agent's stated confidence without empirical validation | Forecast Ledger calibration shrinkage; action gate operates on `F_AI_calibrated`, not raw `F_AI` |
| Agent silently tracking the Market-State Baseline (no incremental edge) | Baseline isolation (code-level: `agents/` cannot import from `baseline/`); incremental-AI-edge audit column |
| Promoted skills overfit on historical replay | Multi-split holdout (regime, sector, time, cross-model) |
| Evaluator becomes the target (Goodhart) | Scoreboard not scalar; promotion uses vector, not single number |
| Regime change invalidates calibration | Per-signal-class reliability tracked over rolling windows; drift detectors; periodic re-validation across regimes |
| Reflexivity at production size | Capacity-adjusted scoring; deployable edge ≠ nominal edge |
| Model lock-in | Model swap test in week 12; year-2 fine-tune plan; population mechanic |
| Narrative drift | Realized returns are the only ground truth |
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
