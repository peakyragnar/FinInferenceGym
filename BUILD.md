# FinInferenceGym — Build Plan

The practical 12-week execution plan, derived from and constrained by [DESIGN.md](DESIGN.md). DESIGN.md commitments are non-negotiable; this plan is how we honor them during build. If a build step would violate a commitment, the build step changes, not the commitment.

Each phase has five components:

- **Teaching** — intuition reinforcement + domain expertise Michael needs.
- **Build** — concrete deliverables.
- **DESIGN.md commitments addressed** — explicit cross-reference.
- **Exit criterion** — what proves the phase is done.
- **Slippage watch** — specific traps that would violate DESIGN.md, called out so we can catch them in flight.

---

## Scope and Budget

- **Time**: 12 weeks. ~720 hours of build (10 hrs/day × 6 days/week).
- **Budget**: $11–17K total (data + APIs + minimal compute + infrastructure). Reduced from $12–18K because the transcript corpus is now an existing asset.
- **End state**: Live, calibrated, model-pluggable Bayesian decision system; population of agents; memory accumulating; trajectory store ready for year-2 own-model fine-tune.

### Universe (stratified)

Three tiers, each with a different purpose. Per DESIGN.md, the production universe is broad — narrowing it by preference is bias-import.

| Tier | Size | Purpose |
|---|---|---|
| **Learning / toy universe** | ~30 names | Used in Phase 0–2 to validate the evaluator and agent pipeline against known ground truth. **Not the production universe.** |
| **Production analytical universe** | ~1700+ names | Full transcript corpus plus delisted shadow universe and any reachable names with PIT fundamentals/prices. The system forms beliefs and identifies edges across all of these. |
| **Active capital universe** | emergent | The subset where, in any period, calibrated edge × capacity × Kelly justifies capital deployment. Emerges from the analytical universe — not pre-defined. |
| **Delisted shadow universe** | varies | PIT fundamentals + prices for companies that delisted in the window. Counters survivorship bias of the transcript corpus. **Critical mitigation.** |

All tiers selected by operational + structural criteria only (no thematic tilt — see DESIGN.md "Operational Constraints").

### Scoring horizons

Every belief is scored against time-revealed labels at multiple horizons in parallel: **1 month, 3 months, 6 months, 1 year.** Toy/learning episodes may use shorter horizons for fast iteration. The system discovers empirically at which horizon each agent has edge. The system never pre-commits to a single horizon.

### Action space

The full equity complex. Each agent's terminal output includes belief over state, recommended **expression** (chosen from the space below), sizing (fractional Kelly), and horizon-of-edge.

- **Equity**: long, short.
- **Options**: calls, puts, vertical / calendar / diagonal spreads, straddles, strangles.
- **Volatility**: long vol, short vol, dispersion, vol-calendar.
- **Pairs / relative-value**: within the equity complex (e.g., long A / short B; long A-call / short B-call).
- **NO-EDGE**: default when no expression has positive net-of-cost edge.

Expression is chosen for asymmetric payoff capture and capacity, not for stylistic preference.

### Existing Data Assets

- **Transcript corpus**: 10 years × 1700 companies. Speaker-tagged, timestamped. Quality not yet verified.
- **Transcription pipeline**: existing script. Quality not yet verified.
- **Known biases**:
  - **Survivorship**: all 1700 currently trading. Delisted/bankrupt/acquired companies excluded. This is *the most dangerous bias for state-inference*, because the worst decay trajectories are absent from the data. Mitigation: delisted shadow universe (Norgate fundamentals + prices) used in promotion gate.
  - **Tech-weighted**: corpus emphasizes tech sector coverage. Mitigation: sector-split validation in promotion gate (Phase 4); skills that only work in tech are tagged tech-restricted.
- **QA status**: not done. Phase 1 week 1 is corpus QA, before any other Phase 1 work.

---

## Design-to-Build Cross-Reference

Where each DESIGN.md commitment is operationalized in the build. A commitment that doesn't appear in any phase has slipped.

| DESIGN.md Commitment | Phase(s) | What gets built |
|---|---|---|
| #1 Evaluator load-bearing | 0 | Scoreboard, proper scoring rules, process metrics, multi-horizon scoring |
| #2 Belief over hidden state | 0, 2 | State-belief scoring; agent outputs are beliefs over state |
| #3 Time one-way valve | 1 | PIT discipline, live-feed parity, look-ahead audits |
| #4 Verified updates only | 4 | Promotion gate (held-out + live + cross-model + survivorship + domain-of-validity) |
| #5 Cognition/verification boundary | 0, 2 | Typed model interface; cognition stays in model side |
| #6 Raw-evidence native reasoning | 1, 2 | Raw-evidence channel; model-driven agent on raw evidence |
| #7 Intelligence in architecture | 0, 1 | Model-agnostic memory format; swappable model interface |
| #8 Two-axis improvement | 1, 5 | Trajectory store in SFT-fit format; year-2 fine-tune plan |
| #9 Population, not single agent | 4 | ≥3 agent variants spawned; population mechanics |
| #10 Michael as auditor only | every | Phase-gate audit by Michael; no Michael-comparison signal |
| **Broad production universe** | 1, 2 | ~1700+ names in analytical universe; deployment is emergent subset |
| **Multi-horizon scoring** | 0, 2, 4 | 1m / 3m / 6m / 1y scored in parallel; horizon-tagged skills |
| **Full equity-complex action space** | 0, 2 | Equity / options / vol / pairs / no-edge; expression-tagged skills |

If you finish a phase and any commitment cell looks empty, something has slipped.

---

## Build Principles

- **No scaffolding.** Don't build what won't be used.
- **Toys before live.** Every metric and evaluator is tested on toys with known ground truth before being applied to finance.
- **Teach alongside.** Each phase deepens intuition for the primitive being built AND the domain knowledge required.
- **Lock principles; iterate execution.** [DESIGN.md](DESIGN.md) does not change because of execution friction. Execution adapts to honor design.
- **Phase-gate audit by Michael.** Every phase ends with the audit questions from DESIGN.md. Any slippage stops the line.

---

## Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2)

### Teaching

**Intuitions reinforced**:
- [Intuition 1: Belief Revision Under Evidence](intuitions.md#1-belief-revision-under-evidence)
- [Intuition 2: Calibration Over Confidence](intuitions.md#2-calibration-over-confidence)
- [Intuition 7: Calibrate the Evaluator in a Toy First](intuitions.md#7-calibrate-the-evaluator-in-a-toy-first)

**Domain expertise**:
- **Proper scoring rules.** Brier vs log score, when each applies, how each behaves at tails.
- **Calibration vs discrimination.** Two distinct dimensions of belief quality.
- **Reliability diagrams.** Diagnostic tool for over/underconfidence by probability bucket.
- **Process metrics vs outcome metrics.** Did the agent update on emissions vs price.
- **Typed model-call interfaces.** Why the contract between system and model must be defined before any model is plugged in. This is the cognition/verification boundary in code.
- **Memory artifact format.** Why memory must be model-agnostic from day 1 (DESIGN.md #7).

### Build

- **Evaluator v0** — scoreboard library. Takes (belief, action, outcome) tuples and returns a vector of metrics: Brier, log score, calibration curve, process-quality flag, decision-quality score, capacity-adjusted return.
  - **Multi-horizon scoring built in from day 1.** Each belief is paired with labels at 1m / 3m / 6m / 1y (toys may use shorter for fast iteration). The evaluator scores at all horizons in parallel and tracks per-horizon calibration separately.
  - **Action-space-aware scoring.** Each action carries an `expression_type` tag (equity-long / equity-short / option-call / option-put / option-spread / option-straddle / vol-long / vol-short / pair / no-edge). Per-expression performance tracked separately so the system can discover where edge lives.
- **Coin toy + 3-state synthetic company toy.** Known ground truth. The evaluator is validated against these.
- **Adversarial test agents** — confidently-wrong, always-50%, well-calibrated. Verify the evaluator distinguishes them.
- **Model interface contract** — typed I/O specification. Inputs: raw evidence. Outputs: structured terminal data (belief over state + recommended expression + sizing + horizon-of-edge + uncertainty + proposed memory updates). The contract is the same regardless of which model is plugged in.
- **Memory artifact schema** — versioned, model-readable format. Skills, hypotheses, observations, lessons. Specified as YAML/JSON files in a versioned registry. Schema includes horizon-tagging and expression-type-tagging fields so skills carry their domain of validity.

### DESIGN.md commitments addressed

- #1 (evaluator), #2 (belief over state), #5 (cognition/verification boundary in code), #7 (memory format model-agnostic).

### Exit criterion

- Evaluator correctly orders adversarial agents on every scoreboard dimension.
- Reliability diagrams show overconfidence in the confidently-wrong agent and zero discrimination in the always-50% agent.
- Model interface contract is documented; a stub agent compiles against it.
- Memory schema is documented and validates a sample skill artifact.

### Slippage watch

- **Pre-engineered features.** Are we tempted to put feature extraction into the evaluator or interface layer? No. The model sees raw evidence (Phase 1 onward).
- **Templated reasoning.** Is the model interface forcing a specific reasoning structure? No. Only terminal output is structured.
- **Model lock-in.** Is anything in the contract specific to one model's quirks? No. The contract is provider-agnostic.

---

## Phase 1 — Data Spine + Raw-Evidence Channel (Weeks 3–4)

### Teaching

**Intuitions reinforced**:
- [Intuition 4: Time Grades the Agent](intuitions.md#4-time-grades-the-agent)

**Domain expertise**:
- **Point-in-time data.** Restatements, revisions, as-of vs as-known dates.
- **Look-ahead bias.** Specific failure modes (restated financials, current S&P membership for past dates, post-close prices).
- **Corporate actions.** Splits, dividends, spinoffs. Total-return vs price-return.
- **Survivorship bias.** Universes built from "still trading today."
- **Vendor evaluation.** What to ask. Norgate, FactSet PIT, IBKR.
- **Live-feed parity.** Replay and live must produce byte-identical outputs for same as-of date.
- **The raw-evidence channel.** What the model sees: full transcripts, full options chains, multi-quarter histories, peer data, macro context. **Not pre-digested.**

### Build

**Week 1 — Corpus QA before anything else.**
- **Stratified sample of ~30 transcripts** across companies / years / quarters. Manual read: speaker-tagging accuracy, Q&A delineation, timestamp correctness, missing sections, hallucinated content from speech-to-text errors.
- **Statistical scan of all ~40K transcripts**: length distribution, missing fields, duplicate detection, company-name to CUSIP/ticker normalization.
- **Spot-check against IR-website transcripts** for 5 names across the time window to verify accuracy.
- **Outcome**: corpus passes QA / corpus has fixable issues / corpus must be scoped to clean subsets. We do not build on dirty data. If the pipeline has systematic issues, fix or scope before proceeding.

**Week 1–4 — Data spine and channels.**
- **Stratified universe selection** by operational + structural criteria across all tiers (learning ~30, production analytical ~1700+, delisted shadow ~all available). Sector-balanced within constraints. Documented selection criteria.
- **Vendor selection + ingest** — Norgate Premium (PIT fundamentals + prices for **all in-scope names including delisted** — non-negotiable) + IBKR (live + options) + transcript corpus from existing dataset.
- **Delisted shadow universe** — Norgate's delisted-name fundamentals + prices ingested as a first-class data set. Used by the promotion gate (Phase 4) to test for survivorship-bias in transcript-derived skills.
- **Options data coverage.** Options chain history for the subset of names with meaningful options markets (typically ~500 of the ~1700). CBOE DataShop subset or OptionMetrics via WRDS. Live options via IBKR.
- **Six-data-type schema** — canonical formats with `as_of`, `as_known`, `source`, `version`, `corpus_bias` flag where applicable.
- **Replay pipeline** — given an as-of date, returns exactly what was knowable then. Includes delisted-name data for as-of dates when those companies were still trading.
- **Live pipeline** — structurally identical to replay.
- **Raw-evidence channel** — typed pipe that delivers full unprocessed evidence (transcripts, options chains, histories, filings) to a model on demand for any in-scope name. **No feature extraction at this layer.**
- **Trajectory store** — every belief, action, outcome, score is written to disk in SFT-fit format from day 1 (DESIGN.md #8 — year-2 own-model path). Each record tagged with horizon and expression-type. The transcript corpus is preserved with full speaker-turn structure and timestamps so it's available for year-2 fine-tuning.
- **Parity tests** — sample as-of dates verified byte-for-byte between replay and live across multiple names spanning the analytical universe.

### DESIGN.md commitments addressed

- #3 (time one-way valve), #6 (raw-evidence native reasoning — the channel that makes it possible), #7 (model-agnostic data format), #8 (trajectory store in SFT-fit format from day 1).

### Exit criterion

- Transcript corpus QA complete; either passed clean or scoped to a clean subset with documentation.
- Replay matches live byte-for-byte across multiple sample dates.
- No look-ahead leak passes adversarial test (as-of 2020-Q3 cannot reveal anything published in 2020-Q4 or later).
- Raw-evidence channel delivers full unprocessed evidence for any (company, as_of_date).
- Delisted shadow universe is ingested and queryable; sample delisted-name retrieval works.
- Trajectory store schema is documented; a sample trajectory writes and reads cleanly.

### Slippage watch

- **Feature engineering creeping into the spine.** Are we tempted to compute "sales_cycle_elongation_delta" or similar in the spine? No. That's a search-time choice the model makes. The spine delivers raw.
- **Transcript summarization.** Are we tempted to summarize transcripts rather than deliver full speaker-tagged text? No. Full text only.
- **Survivorship bias smuggling.** Are we using the transcript corpus alone for any calibration or training task that should include delisted outcomes? No. Delisted shadow universe is part of every relevant validation step.
- **Skipping QA.** Are we tempted to skip corpus QA and start ingesting? No. Dirty data poisons everything downstream.
- **Trajectory format compromise.** Is the trajectory store missing something needed for year-2 SFT (e.g., reasoning traces, intermediate beliefs)? Fix in Phase 1, not later.

---

## Phase 2 — Model-Driven Agent on Raw Evidence (Weeks 5–6)

### Teaching

**Intuitions reinforced**:
- [Intuition 3: The Hidden State Is the Real Object](intuitions.md#3-the-hidden-state-is-the-real-object)
- [Intuition 5: Inference, Not Pattern Matching](intuitions.md#5-inference-not-pattern-matching)
- [Intuition 11: The Market Is a Second Believer](intuitions.md#11-the-market-is-a-second-believer)

**Domain expertise**:
- **Hidden state modeling.** Coarse vs fine state spaces. Why coarse is virtuous initially.
- **Implied DCF math.** Solving in reverse.
- **Options-implied probabilities.** Risk-neutral vs real-world.
- **Market-implied belief recovery.** Inverting price to recover the market's implied state belief.
- **Edge calculation.** `your belief − market-implied belief`, net of costs.
- **Fractional Kelly sizing.** 0.25× to 0.5× Kelly to absorb miscalibration.
- **The cognition/verification boundary in practice.** Model reasons freely; structured output is the only thing scored.

### Build

- **Pure-code plumbing baseline** — hand-coded Bayesian with hardcoded likelihoods on the ~30-name learning universe. **Used ONLY to verify the data spine + evaluator + market-implied belief pipeline are correctly wired.** This is *not* the production agent. Its outputs are discarded after plumbing validation; its hand-coded heuristics are never promoted into the model agent.
- **First model-driven agent** — receives raw evidence from the channel built in Phase 1, reasons natively, produces structured terminal output (belief over state + recommended expression from the full equity complex + sizing + horizon-of-edge + uncertainty + memory updates). Operates on the **production analytical universe** (~1700 names). This *is* the production agent shape. (DESIGN.md #5, #6.)
- **Market-implied belief recovery module** — implied DCF + options-implied probabilities. Used by both agents.
- **Edge calculator** — computes edge per (name × horizon × expression) cell. Each agent decides which cells have edge worth acting on.
- **Fractional-Kelly sizer** — applied per expression at the chosen horizon.
- Both agents run on the same evaluator. Both scored at all horizons. The pure-code baseline only operates on the learning universe; the model-driven agent operates on the production analytical universe.

### DESIGN.md commitments addressed

- #2 (belief over hidden state), #5 (cognition/verification boundary — model reasons freely; structured output only), #6 (raw-evidence native reasoning).

### Exit criterion

- Pure-code baseline runs correctly, validating the data + evaluator + market-implied belief pipeline. (Plumbing OK.)
- Model-driven agent runs on historical replay, produces sensible structured terminal output, scored by evaluator.
- Both beat the null-agent baseline on calibration. (If they don't, something is broken — fix before proceeding.)

### Slippage watch

- **Promoting pure-code heuristics into the model agent.** No. Pure-code is plumbing only. Its likelihood hand-codings are not memory items for the model agent.
- **Pre-extracting features for the model agent.** No. The model agent sees raw evidence and chooses what to attend to.
- **Templating the model agent's reasoning.** No. The prompt enables the model to reason however it reasons; only the terminal output schema is enforced.
- **Single-model lock-in.** This phase uses one model for simplicity, but the contract is provider-agnostic. The first model used must be swappable in Phase 5 with no code changes.

---

## Phase 3 — Live Deployment + Memory Activation (Weeks 7–8)

### Teaching

**Intuitions reinforced**:
- [Intuition 13: Time and the Two Ways to Be Wrong](intuitions.md#13-time-and-the-two-ways-to-be-wrong)
- [Intuition 14: Reflexivity](intuitions.md#14-reflexivity-your-own-trades-are-emissions) (initially small but framework accepts it)

**Domain expertise**:
- **Live-feed engineering.** Market hours, holidays, halts, after-hours.
- **Real-time timestamp discipline.** `as_known` ≠ source emission time.
- **Recovery without info leak.** Outage handling must not retro-fill.
- **Process metrics in production.** Live dashboards.
- **Memory artifact lifecycle.** Proposed → probationary → promoted → retired.

### Build

- **Live operation** of model-driven agent (pure-code agent continues in parallel for plumbing parity verification only).
- **Memory activation** — agent can write proposed memory items into the registry. Items are flagged "proposed" — they do not yet affect the agent's future inference because the promotion gate (Phase 4) hasn't been applied. We are *only* collecting candidate memory at this stage.
- **Full logging** — every input, belief, action, score in the trajectory store with full provenance.
- **Calibration diagnostics dashboard** — daily reliability diagram, Brier rolling average, process-quality flag.
- **No Michael comparison.** Agent's outputs are scored only against time-revealed labels. (DESIGN.md #10.)

### DESIGN.md commitments addressed

- #3 (time one-way valve in live operation), #8 (trajectory store accumulating live trajectories for year-2 SFT), #10 (no Michael comparison).

### Exit criterion

- Live calibration metrics over 4+ weeks match historical-replay calibration within tolerance.
- Memory proposals are being generated (rate documented).
- No Michael-discretion signal anywhere in the evaluation pipeline.

### Slippage watch

- **Michael comparison creeping in.** Is there any dashboard, alert, or metric that compares agent calls to Michael's discretion? No. Remove if found.
- **Promoting unverified memory.** Is any "proposed" memory item being used by the live agent for inference? No. Only promoted (Phase 4) items affect inference.
- **Look-ahead leaks during live.** Live exposes leaks replay missed. Treat any leak as a stop-the-line event.

---

## Phase 4 — Population + Promotion (Weeks 9–10)

### Teaching

**Intuitions reinforced**:
- [Intuition 9: Costly Observation](intuitions.md#9-costly-observation) (applies to API costs)
- [Intuition 10: Which Information to Buy](intuitions.md#10-which-information-to-buy)

**Domain expertise**:
- **Population dynamics.** Spawning variants. Diversity vs convergence.
- **LLM API cost economics.** Token pricing, caching, model-tier routing.
- **Goodhart resistance.** Why a memory item improving a single metric is suspect.
- **Held-out methodology.** Time / regime / sector / cross-model splits.
- **Cross-model regression.** A skill must transfer across models or it's overfit to one.

### Build

- **Spawn ≥2 more agent variants** — varying in (model × memory subset × prompt structure × reasoning approach). Now we have ≥3 agents in parallel. (DESIGN.md #9 — population is the unit of search.)
- **LLM-as-proposer integrated** — when an agent fails an episode, a model proposes a candidate memory addition. Proposal is a hypothesis.
- **Promotion gate** — any memory addition must:
  1. Improve held-out replay calibration on ≥2 of 4 split types (time, regime, sector, cross-model).
  2. Improve or maintain live calibration over a 2-week probationary period.
  3. Not violate process discipline.
  4. Pass cross-model regression — validated under ≥2 model engines.
  5. **Pass the survivorship check** — a skill that uses transcript evidence must not systematically miss decay states. Tested against the delisted shadow universe using whatever subset of evidence the model would have had access to (typically fundamentals + prices only, since most delisted names lack transcripts). Skills that calibrate well on survivors but flop on delisted names are rejected.
  6. **Declare its domain of validity.** A skill that only works at the 3-month horizon is tagged `horizon: 3m`. A skill that only works for equity-direction expressions is tagged `expression_type: equity_directional`. A skill that only works in a specific sector is tagged accordingly. **A skill that claims universal applicability must demonstrate it across horizons and expression types; otherwise it gets the narrower tag and is deployed only where the tag applies.** This prevents skills from leaking out of their validity domain.
- **Cost monitoring** per agent with daily/weekly summaries.
- **Memory promotion log** — every proposal recorded with outcome (promoted / rejected / probationary). Both successes and failures preserved for audit.

### DESIGN.md commitments addressed

- #4 (verified updates only — promotion gate), #5 (cognition/verification boundary — proposer is model, gate is system), #9 (population, not single agent).

### Exit criterion

- ≥3 memory items survived the promotion gate and are demonstrably improving live calibration.
- ≥3 agents running in parallel with documented variance in (model × memory × prompt).
- Cost tracking within budget.

### Slippage watch

- **Agent grading itself.** Is any agent's output being used to validate its own memory proposals? No. Cross-agent evaluation only.
- **Promotion threshold relaxation.** Are we tempted to lower the bar when proposals don't pass? No. If proposals consistently fail, the issue is the proposer or the agent, not the gate.
- **Population convergence.** Are agents producing the same outputs? Diversity must be preserved; if they converge, the variants weren't varied enough.
- **Bias-import via memory proposals.** Is the LLM proposing items that smuggle in narrative ("AI will reshape this industry")? Promotion gate filters; reject narratives that don't translate into testable predictions.
- **Survivorship-check skipping.** Is any transcript-derived skill being promoted without testing against the delisted shadow universe? No. The survivorship check is non-negotiable for any skill that uses transcript evidence.

---

## Phase 5 — Model Swap Validation + Year-2 Path (Weeks 11–12)

### Teaching

**Intuitions reinforced**:
- The ride-the-exponent principle (DESIGN.md). This phase proves it.

**Domain expertise**:
- **Model swap methodology.** Procedure for qualifying a new model.
- **Open-weights deployment.** Llama / Qwen / DeepSeek. Local or rented GPU.
- **SFT data preparation.** Formatting trajectories for fine-tuning.
- **Year-2 fine-tune trigger criteria.** When trajectory volume + memory maturity warrant.
- **Capacity-adjusted scoring.** Realistic market-impact assumptions for retail size.

### Build

- **Cross-model swap test** — run the population under ≥2 frontier models (Claude, Gemini, GPT) AND ≥1 open-weights model. Validate all promoted memory items survive.
- **Capacity-adjusted scoring** added to evaluator. Score deployable edge, not nominal edge.
- **SFT data preparation** — trajectory store inspected; formatted for year-2 fine-tuning. Sample fine-tune executed on a small open-weights model to verify pipeline.
- **Year-2 plan document** — concrete plan: data accumulation goals, fine-tune trigger criteria, universe expansion conditions, capacity scaling thresholds, own-model deployment plan.

### DESIGN.md commitments addressed

- #6 (raw-evidence native reasoning — proven by working under multiple models), #7 (intelligence in architecture — proven by model swap), #8 (two-axis improvement — year-2 SFT path operational), #9 (population — running on diverse engines).

### Exit criterion

- System has measurable edge vs market baseline on at least one decision class, after costs and capacity adjustment.
- Model swap test passed: system functions and maintains calibration under each tested model.
- Year-2 plan documented and approved by Layer 5 audit.

### Slippage watch

- **Year-2 plan becoming aspirational.** Is the plan concrete enough to execute? Specific data targets, specific fine-tune triggers, specific deployment criteria. If vague, sharpen.
- **Open-weights performance gap.** If even the strongest local-runnable open-weights model fails, the year-2 own-model path is at risk. This must be addressed before relying on it.
- **Capacity assumptions optimistic.** Are we using realistic market-impact estimates for retail size? If not, our "edge" is fictional.

---

## Phase-Gate Audit (After Each Phase)

Michael's standing audit at every phase boundary. Asked of the build, not asked of Michael.

1. Did we add any constraint not explicitly justified by [DESIGN.md](DESIGN.md)?
2. Did we smuggle a thematic prior, narrative anchor, or "obviously X"?
3. Did anything migrate *out of* verification and *into* cognition?
4. Is the model interface still open?
5. Is the evaluator still honest? (Adversarial toy re-test.)
6. Is data discipline holding? (Parity test re-run.)
7. Is the trajectory store still SFT-fit?
8. **Is the delisted shadow universe being applied consistently?** Any transcript-derived skill must clear the survivorship check.
9. Are we on budget? Are we on schedule?

**Any failure of #1, #2, #3, or #4 is a stop-the-line.** Address before proceeding.

---

## What This Plan Deliberately Does Not Include

- **Pre-training a custom model.** Year 2 at earliest. Listed in DESIGN.md year-2 outlook.
- **AlphaEvolve as a separate framework.** The population + promotion architecture *is* AlphaEvolve over agents — we instantiate the pattern, not import the framework.
- **Continual Harness as a separate framework.** Same — LLM-as-proposer + memory + promotion is Continual Harness simplified.
- **RL on action policies as a primary mechanism.** Year 2+. Only after the evaluator is rock-solid and trajectory volume is sufficient.
- **Multi-model committee / jury (Garry Tan-style).** Determined to not add enough value over RAG + promotion gates. Single-specialist pipelines are cleaner.
- **Sharpe optimization.** Out of scope per DESIGN.md.
- **Universe expansion based on thematic views.** All thematic views are outputs of the system, not inputs.
- **Single-agent architecture.** Population from Phase 4 forward.
- **Pre-engineered features as primary model input.** Forbidden by DESIGN.md #6.
- **The "system ↔ Michael" comparison matrix.** Forbidden by DESIGN.md #10.
- **Pre-committed horizon, expression, or narrow production universe.** Multi-horizon, full equity complex, broad production universe per DESIGN.md "Operational Constraints."
- **HFT, market-making, cross-asset.** Structural exclusions per DESIGN.md, not preferences.

---

## Iteration Policy

This document updates as we execute. The schema (phases, teaching, build, design cross-reference, exit, slippage watch) stays stable. The specifics (which vendor, which model, which exit numbers) evolve. Every meaningful update is logged so we can audit how the build deviated from the plan and why.

When we move to a new context window: read [DESIGN.md](DESIGN.md) first, then this file, then check current phase status. See [CLAUDE.md](CLAUDE.md) for the session-restoration protocol.
