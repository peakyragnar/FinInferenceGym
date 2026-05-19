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
| #1 Evaluator load-bearing | 0, 1 | Scoreboard, proper scoring rules, process metrics; all columns populated and adversarially tested in Phase 1 NEW toy extension |
| #2 Forecast distribution over realized returns, calibrated empirically | 0, 1, 2 | Brier / log_score / reliability_buckets (Phase 0); Forecast Ledger MVP + calibration shrinkage + Tradable-Edge Action Engine (Phase 1 NEW Clusters A, B); Market-State Baseline isolation (Phase 1 NEW Cluster I); real-data versions (Phase 2 NEW) |
| #3 Time one-way valve | 1, 2 | Toy restatement events + delisted-mid-trajectory (Phase 1 NEW Cluster E); PIT discipline + `time_leak_guard` on real data (Phase 2 NEW Stone 24) |
| #4 Verified updates only | 1, 4 | Toy promotion gate exercises the four-check mechanism (Phase 1 NEW Cluster G); production promotion gate operates on real evidence (Phase 4) |
| #5 Cognition/verification boundary | 0, 1 | Typed model interface; first LLM cognition with structured Contract output (Phase 1 NEW Cluster F); Baseline isolation enforced by import-linter (Phase 1 NEW Cluster I) |
| #6 Raw-evidence native reasoning | 1, 2 | LLM reads toy emissions as raw text (Phase 1 NEW Cluster F); raw-evidence channel on real data (Phase 2 NEW Stone 28) |
| #7 Intelligence in architecture | 0, 1 | Model-agnostic memory format (Phase 0); memory + promotion gate exercised end-to-end in toy (Phase 1 NEW Cluster G) |
| #8 Two-axis improvement | 1, 2, 5 | Trajectory store with toy v5 Contracts (Phase 1 NEW); real v5 Contracts (Phase 2 NEW Stone 27); year-2 fine-tune plan (Phase 5) |
| #9 Population, not single agent | 1, 4 | ≥3 LLM agent variants in toy with documented diversity (Phase 1 NEW Cluster H); population on real data (Phase 4) |
| #10 Michael as auditor only | every | Phase-gate audit by Michael; no Michael-comparison signal |
| **Broad production universe** | 2 | ~1700+ names in analytical universe; deployment is emergent subset |
| **Multi-horizon scoring** | 0, 1, 4 | reliability_buckets (Phase 0); multi-horizon realized returns in toy (Phase 1 NEW Cluster D); horizon-tagged skills (Phase 4) |
| **Full equity-complex action space** | 1, 2 | Action layer first instantiated in toy (Phase 1 NEW Cluster B); full equity complex on real data (Phase 2 NEW onward) |

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
- **Calibration vs discrimination.** Two distinct dimensions of forecast quality.
- **Reliability diagrams.** Diagnostic tool for over/underconfidence by probability bucket.
- **Process metrics vs outcome metrics.** Did the agent update on emissions vs price.
- **Typed model-call interfaces.** Why the contract between system and model must be defined before any model is plugged in. This is the cognition/verification boundary in code.
- **Memory artifact format.** Why memory must be model-agnostic from day 1 (DESIGN.md #7).

### Build

- **Evaluator v0** — scoreboard library. Takes (forecast, action, realized return) tuples and returns a vector of metrics: Brier, log score, reliability buckets, process-quality flag, decision-quality score, capacity-adjusted return.
  - **Multi-horizon scoring built in from day 1.** Each forecast is paired with realized returns at 1m / 3m / 6m / 1y (toys may use shorter for fast iteration). The evaluator scores at all horizons in parallel and tracks per-horizon calibration separately.
  - **Action-space-aware scoring.** Each action carries an `expression_type` tag (equity-long / equity-short / option-call / option-put / option-spread / option-straddle / vol-long / vol-short / pair / no-edge). Per-expression performance tracked separately so the system can discover where edge lives.
- **Coin toy + 3-state synthetic company toy.** Known ground truth. The evaluator is validated against these. (The toy was originally two-believer per the pre-v5 framing; v5 collapses it to single-believer over realized returns — refactor lands in Phase 1 NEW Cluster A.)
- **Adversarial test agents** — confidently-wrong, always-50%, well-calibrated. Verify the evaluator distinguishes them.
- **Model interface contract** — typed I/O specification. Inputs: raw evidence. Outputs: structured terminal data (forecast distribution over realized returns + signal-class tag + recommended expression + sizing + horizon-of-edge + uncertainty + proposed memory updates). The contract is the same regardless of which model is plugged in.
- **Memory artifact schema** — versioned, model-readable format. Skills, hypotheses, observations, lessons. Specified as YAML/JSON files in a versioned registry. Schema includes horizon-tagging and expression-type-tagging fields so skills carry their domain of validity.

### DESIGN.md commitments addressed

- #1 (evaluator), #2 (forecast-over-realized-returns primitives — Brier, log_score, reliability_buckets), #5 (cognition/verification boundary in code), #7 (memory format model-agnostic).

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

## Phase 1 — Toy Architecture Extension (Weeks 3–6)

> Reordered 2026-05-16 (v4) and reformulated 2026-05-18 (v5). See [DECISIONS.md "Constitution tightening v4: Phase 1 reorder"](DECISIONS.md#constitution-tightening-v4-2026-05-phase-1-reorder) and [DECISIONS.md "Constitution tightening v5"](DECISIONS.md#constitution-tightening-v5-2026-05-belief-over-realized-returns-forecast-ledger-isolated-market-state-baseline).

Phase 1 NEW extends the synthetic-market toy ([src/fingym/toys/synthetic_market.py](src/fingym/toys/synthetic_market.py)) *upward through the full architecture* before any real data is ingested. Each architectural piece — Forecast Ledger MVP, calibration shrinkage, Tradable-Edge Action Engine, cost models, multi-horizon scoring, PIT discipline + restatements + delisted analogs, LLM-driven agent, memory + promotion gate, population mechanic, Market-State Baseline isolation — gets built and validated against the toy world FIRST. Real data substitutes into the toy-trained architecture in Phase 2 NEW, one data type at a time.

The synthetic still CANNOT validate alpha (per DESIGN.md "Three Arenas" — only real-data realized returns score). Phase 1 NEW validates every architectural property EXCEPT alpha. Alpha validation begins in Phase 2 NEW.

### Teaching

**Intuitions reinforced**:
- [Intuition 4: Time Grades the Agent](intuitions.md#4-time-grades-the-agent) — extended to multi-horizon realized returns
- [Intuition 5: Inference, Not Pattern Matching](intuitions.md#5-inference-not-pattern-matching) — first applied to a real LLM (Cluster F)
- [Intuition 13: Time and the Two Ways to Be Wrong](intuitions.md#13-time-and-the-two-ways-to-be-wrong) — toy emits restatements (Cluster E)

**Domain expertise**:
- **Realized returns as the predicted object.** No hidden-state categorization. The toy emits a realized return at horizon; the agent forecasts a distribution over it.
- **Per-signal-class empirical reliability.** A Forecast Ledger records every (forecast, realized return) pair indexed by signal class and computes empirical reliability — the realized truth rate among forecasts that claimed a given probability bucket. Reliability is a measured property, not an a-priori model.
- **Calibration shrinkage.** The agent's raw forecast is shrunk toward its per-signal-class empirical reliability before action.
- **Calibrated expected utility and margin of safety.** Action is gated on calibrated expected utility (Kelly under the shrunk distribution) clearing a margin-of-safety threshold that absorbs costs.
- **Market-State Baseline isolation.** A separate code path runs only on toy headline observables; its forecast is hidden from the AI Core; attribution columns measure incremental AI edge.
- **Cost economics in trade-sizing.** Spread, impact, alpha decay; the difference between nominal calibrated expected utility and realized edge.
- **Multi-horizon scoring.** Same forecast pipeline, different realized-return horizons; per-horizon reliability tracked separately.
- **Restatements + delisting.** What changes when `as_known(t) ≠ as_known(t+k)`; what happens when a name disappears mid-trajectory.
- **LLM-as-agent.** Reading raw evidence as text; emitting a v5 Contract that the validator accepts.
- **Memory promotion mechanism (not yet memory content).** The four-check gate as plumbing, exercised against toy-generated memory proposals.
- **Population mechanics.** Multiple LLM variants, scored in parallel, with documented diversity.

### Build

Nine clusters, each ~3-4 tight sub-stones (concept-in-chat → code → verify, same texture as Phase 0). ~27-30 sub-stones total.

**Cluster A — Single-believer toy refactor + Forecast Ledger MVP (Stones 7b, 11b)**. Toy emits realized returns at horizon (single-believer; the prior two-believer setup is gone). Forecast Ledger records each (forecast, realized return) pair indexed by signal class. Per-signal-class reliability is computed empirically over many forecasts and stored as a derived view of the data spine.

**Cluster B — Calibration shrinkage + Tradable-Edge Action Engine (Stones 11c, 11d)**. Calibration shrinkage applies per-signal-class reliability to the agent's raw forecast to produce `F_AI_calibrated`. The Action Engine computes calibrated expected utility (Kelly under the shrunk distribution) and gates action on a margin-of-safety threshold. Action selection (long / short / NoAction) follows the gate. `calibrated_expected_utility`, `tradable_edge_score`, and the action-gate verdict become scoreboard columns.

**Cluster C — Cost models + capacity (Stone 14)**. Per-name toy liquidity + spread + impact + alpha decay. `realized_edge` column on the scoreboard distinguishes nominal calibrated expected utility from realized edge after costs.

**Cluster D — Multi-horizon scoring (Stone 10 code)**. Toy emits realized returns at multiple tick horizons (e.g., 1-tick / 5-tick / 20-tick). One v5 Contract scored at all horizons in parallel. Per-horizon reliability tracked separately in the Forecast Ledger. Reliability diagrams support horizon filtering.

**Cluster E — PIT discipline + restatements + delisted analogs (Stones 24, 26 in toy)**. Toy emits restatement events: an emission can be issued at `as_of=t` with subsequent restated emission at `as_known=t+k` carrying a different value. Toy companies "delist" mid-trajectory (the emission stream terminates; subsequent realized returns still arrive at known horizons for evaluation). `time_leak_guard` fires structurally on the toy emission stream.

**Cluster F — LLM-driven agent (Stone 30, first instantiation)**. First real LLM (Anthropic SDK; `claude-opus-4-7` or comparable). The LLM reads toy emissions as text and emits v5 Contracts (forecast distribution over realized returns + signal-class tag + action + sizing). `contract_validator` accepts the LLM's output. Single agent only; population comes in Cluster H.

**Cluster G — Memory + promotion gate (Stones 39, 40 in toy) ✅ 2026-05-18.** The LLM emits an OPTIONAL `propose_memory_item` tool call alongside its mandatory `submit_forecast`. The toy promotion gate runs checks 1 (held-out replay against the Scoreboard) and 4 (domain-of-validity declared) with real evaluation; checks 2 (cross-model regression) and 3 (survivorship) are stubbed `passed=False` with empty fields — the audit trail is honest about what was and was not validated (see [DECISIONS.md "Honest stubs in the toy-mode promotion gate"](DECISIONS.md)). Toy mode collapses L1+L2 (no probationary tier yet); promoted skills land at `memory_registry/promoted/<id>.yaml` and are read by future `LlmAgent` instances at construction. Cluster H wires up real check 2 and adds the L2 probationary tier; Phase 2 NEW wires up real check 3.

**Cluster H — Population mechanic + real cross-model regression (Stones 38, 40 in toy) ✅ 2026-05-18.** Default population: 3 `LlmAgentVariant` configurations — `haiku_default`, `haiku_value_investor` (different prompt), `sonnet_default`. Variants share the emission stream / Scoreboard / calibrator / Action Engine; differ only on `model` + `prompt_style`. Real check 2 wired up: `evaluate_proposal_cross_model` slices the Scoreboard by `agent_id`, runs check 1 per variant, counts confirming variants; promotes to L3 if ≥`MIN_VARIANTS_PASSING=2` confirm + check 4 passes; lands L2 if ≥1 but <threshold; rejects otherwise. L2 tier real (`memory_registry/probationary/<id>.yaml`). Re-validation cycles (`revalidate(scoreboard, l3_dir, l2_dir)` every 50 new Scoreboard rows) handle L3 ↔ L2 transitions and retire L2 after `MAX_L2_CYCLES=5` without graduation. Check 3 (survivorship) still stubbed pending Phase 2 NEW.

**Cluster I — Market-State Baseline isolation (Stone 11e in toy)**. Toy headline observables (simulated rates / vol / FX-like tick streams) feed a separate `src/fingym/baseline/` module. The Baseline emits its own forecast distribution over realized returns using only those observables. Code-level isolation: `src/fingym/agents/` cannot import from `src/fingym/baseline/` (import-linter rule). The AI Core sees the raw observables the Baseline consumes; it never sees the Baseline's processed forecast. Incremental AI edge column on the scoreboard = AI realized edge minus Baseline realized edge. Validates the isolation pattern in toy mode before real observables substitute in Phase 2 NEW.

### DESIGN.md commitments addressed

- #1 (evaluator load-bearing — all scoreboard columns populated and tested against adversarial agents in the extended toy)
- #2 (forecast distribution over realized returns, calibrated empirically — Forecast Ledger calibration, Tradable-Edge Action Engine gate, isolated Market-State Baseline all exercised in toy mode)
- #5 (cognition / verification boundary — LLM cognition for the first time; structured Contract output is the only thing scored; Baseline isolation enforced at code level)
- #6 (raw-evidence native reasoning — LLM reads toy emissions as text, no pre-engineered features)
- #7 (intelligence in architecture — memory + promotion gate exercised at the mechanism level)
- #9 (population — ≥3 LLM agents in parallel with documented diversity)

### Exit criterion

- All scoreboard columns populated (Brier, log_score, reliability_buckets, per-signal-class reliability, calibrated_expected_utility, tradable_edge_score, realized_edge after costs, incremental_AI_edge over Baseline); each tested against adversarial agents in the extended toy.
- LLM-driven agent produces valid v5 Contracts (`contract_validator` accepts).
- Toy promotion gate produces L2 → L3 promotions on the toy `memory_registry/`; LLM agents read promoted skills at session start.
- Population of ≥3 LLM agents runs in parallel with documented diversity in forecasts and actions.
- Toy Market-State Baseline runs in code-level isolation; `agents/` cannot import from `baseline/` (import-linter rule enforced); incremental AI edge column populated.
- Trajectory store schema instantiated with toy v5 Contracts; ready for the year-2 SFT format.
- All Phase 0 surviving tests still green; mypy strict clean across all source files.

### Slippage watch

- **Synthetic-scores-promote-skills.** Are toy promotion-gate outputs being treated as evidence that a skill generalizes? **NO.** The toy gate validates the MECHANISM. No toy-promoted skill enters production L3 memory. (DESIGN.md "Three Arenas," DECISIONS.md "Worldlets — FUTURE RESEARCH NOT COMMITTED.")
- **Pre-engineered features creeping into the LLM agent (Cluster F).** Is the LLM receiving anything pre-digested instead of raw toy emissions as text? No. Raw emissions only. (DESIGN.md #6.)
- **Templating the LLM's reasoning.** Is the prompt forcing an 11-step reasoning skeleton? No — the Contract IS the constraint; cognition is free. (DECISIONS.md "Constitution tightening v2," rejected synthesis-style 11-step prompt skeleton.)
- **Trusting AI stated confidence without empirical calibration (Cluster B).** Is the Action Engine operating on the agent's raw forecast, or on the calibration-shrunk forecast? Must be the shrunk forecast. The Forecast Ledger's per-signal-class reliability is the non-negotiable input to the gate. (DESIGN.md commitment #2.)
- **Agent reading the Baseline's processed forecast (Cluster I).** Is any code path in `src/fingym/agents/` importing from `src/fingym/baseline/`? Must not — the import-linter rule fires structurally. The AI sees raw observables the Baseline consumes, not the Baseline's processed forecast. (DESIGN.md commitment #2; new failure mode added to DESIGN.md Failure Modes table.)
- **Single-model lock-in (Cluster F).** Does the LLM-driven agent code path embed model-specific quirks? No. Cluster F uses Anthropic for first instantiation, but Cluster H must spawn variants under at least one alternative model (or, at minimum, vary prompt/memory subset over the same model to prove the architecture admits diversity).
- **Skipping cluster discipline.** Each cluster is 3-4 tight sub-stones with concept-in-chat → code → verify. Are we tempted to fuse clusters into one big jump? No — that's how Phase 1 originally drifted into 1700-transcript ingest. Tight stones only.
- **Vendor decisions sneaking in.** Are vendor (SEC EDGAR, FMP, Massive, Norgate) decisions creeping into Phase 1 NEW? No — defer to Phase 2 NEW. The Anthropic API key (Cluster F) is the only external integration.

---

## Phase 2 — Real-Data Transition (Weeks 7–10)

> Reordered 2026-05-16. This was the original Phase 1. See [DECISIONS.md "Constitution tightening v4"](DECISIONS.md#constitution-tightening-v4-2026-05-phase-1-reorder).

Phase 2 NEW substitutes real data into the toy-trained architecture, **one data type at a time**. The architecture from Phase 1 NEW remains the load-bearing structure; real data fills slots that the toy proved out. Vendor decisions are now informed by the FMP/Massive smoke-test findings ([vendor_evaluations/fmp_smoke_test.py](vendor_evaluations/fmp_smoke_test.py), [vendor_evaluations/fmp_comprehensive_test.py](vendor_evaluations/fmp_comprehensive_test.py), [vendor_evaluations/massive_smoke_test.py](vendor_evaluations/massive_smoke_test.py)) — both vendors have the same delisted-coverage gap; FMP additionally has restated-vs-original-as-known issues; SEC EDGAR is the authoritative PIT-fundamentals source.

### Teaching

**Intuitions reinforced**:
- [Intuition 4: Time Grades the Agent](intuitions.md#4-time-grades-the-agent) — at production scale on real timestamps
- [Intuition 9: Costly Observation](intuitions.md#9-costly-observation) — applied to API rate limits and corpus QA scope
- [Intuition 10: Which Information to Buy](intuitions.md#10-which-information-to-buy) — vendor-mix selection

**Domain expertise**:
- **Point-in-time data at production scale.** Real `as_of` / `as_known` mismatches; SEC EDGAR XBRL filings; restatement-event handling on real GE-style events.
- **Vendor evaluation — refined post-smoke-test.** Why no single vendor solves all (prices + fundamentals + transcripts + delisted + headline observables). SEC EDGAR for PIT fundamentals; Massive for prices (with delisted-coverage caveat); existing FMP-derived transcript corpus; FRED for macro headline observables.
- **Headline observable inputs for the Market-State Baseline.** Rates (FRED), realized + implied vol, FX, commodities — the exact source list defines the Baseline's domain of operation. Anything outside this list is not a headline observable; allowing the Baseline to consume non-headline inputs blurs the attribution layer.
- **Live-feed parity.** Replay and live must produce byte-identical outputs for the same as-of date.
- **Survivorship bias at scale.** Why the transcript corpus is survivorship-biased; how to cross-reference SEC EDGAR for delisted CIKs.
- **The raw-evidence channel.** What the model sees in production: full transcripts, full filings, peer data, macro headline observables — never pre-digested. The AI Core consumes the same headline observables the Baseline consumes (raw), but never the Baseline's processed forecast.

### Build

Real-data substitution proceeds stone-by-stone. The previously-Phase-1 deliverables (Stones 22-28) are sequenced as discrete substitution steps:

**Stone 22 — Corpus QA on the existing 10-year / 1700-name transcript corpus**. Stratified sample of ~30 transcripts (manual read: speaker-tagging accuracy, Q&A delineation, timestamp correctness, missing sections, speech-to-text artifacts). Statistical scan of all transcripts (length distribution, missing fields, duplicate detection, company-name to CUSIP/ticker normalization). Spot-check against IR-website transcripts for 5 names. Outcome: passes / has fixable issues / must be scoped to clean subsets. **First real-data step; this is also where the two parked architectural questions (emission-triggered vs agent-driven; emissions taxonomy) reopen** (see DECISIONS.md "Open architectural questions").

**Stone 23 — Six-data-type schema instantiated with real data**. Canonical formats with `as_of`, `as_known`, `source`, `version`, `corpus_bias` flag where applicable. Schema validates against the Phase-1-NEW-trained architecture without architecture changes.

**Stone 24 — PIT discipline at production scale**. `time_leak_guard` fires on real timestamps. Adversarial test: as-of 2020-Q3 cannot reveal anything published in 2020-Q4 or later. Restatement events from SEC EDGAR (the toy Cluster E mechanism, now on real data).

**Stone 25 — Replay vs live parity**. Same code path, real data. Sample as-of dates verified byte-for-byte between replay and live across multiple names.

**Stone 26 — Delisted shadow universe (real vendor)**. SEC EDGAR cross-reference for delisted CIKs (per the FMP/Massive smoke-test findings — neither vendor returns coverage for pre-2024 delisted names; EDGAR is the authoritative source). Ingested as a first-class dataset. Used by the promotion gate (Phase 4) for the survivorship check.

**Stone 27 — Trajectory store with real Contracts**. Schema migrated from toy; sample reads/writes cleanly. Each record tagged with horizon and expression-type. The transcript corpus is preserved with full speaker-turn structure so it's available for year-2 fine-tuning.

**Stone 28 — Raw-evidence channel operational**. Typed pipe delivers full unprocessed evidence (transcripts, filings, prices, fundamentals, headline observables) to a model on demand for any in-scope name. No feature extraction at this layer.

**Stone 11e (real-data) — Market-State Baseline on real observables**. The `src/fingym/baseline/` module (isolated in Phase 1 NEW Cluster I against toy observables) substitutes real headline observables (FRED rates, vol indices, FX, commodities). Code-level isolation continues to hold: `agents/` cannot import from `baseline/`. Incremental AI edge column on the scoreboard now measures real attribution: was the AI's edge from its cognition on raw evidence, or from headline observables anyone has? The Baseline's processed forecast remains hidden from the AI Core; only the raw observables are shared.

### DESIGN.md commitments addressed

- #2 (forecast distribution over realized returns, calibrated empirically — Forecast Ledger and Market-State Baseline operate on real data; calibration shrinkage uses real per-signal-class reliability)
- #3 (time one-way valve — at production scale)
- #6 (raw-evidence native reasoning — the channel that makes it possible, now on real data)
- #7 (model-agnostic data format)
- #8 (trajectory store in SFT-fit format with real v5 Contracts)

### Exit criterion

- The toy-trained architecture works on real data end-to-end for **at least one historical episode of one company** (canary check before broader rollout).
- Transcript corpus QA complete; either passed clean or scoped to a clean subset with documentation.
- Replay matches live byte-for-byte across multiple sample dates.
- Delisted shadow universe (SEC EDGAR-sourced for pre-2024) is ingested and queryable.
- Trajectory store contains real v5 Contracts and reads cleanly.
- Market-State Baseline runs on real headline observables; incremental AI edge column populated on real data; import-linter rule still fires structurally on attempted imports from `agents/` into `baseline/`.
- All Phase 1 NEW tests still green; mypy strict clean.

### Slippage watch

- **Feature engineering creeping into the spine.** Are we tempted to compute "sales_cycle_elongation_delta" or similar in the spine? No. That's a search-time choice the model makes. The spine delivers raw.
- **Transcript summarization.** Are we tempted to summarize transcripts rather than deliver full speaker-tagged text? No. Full text only.
- **Survivorship bias smuggling.** Are we using the transcript corpus alone for any calibration or training task that should include delisted outcomes? No. Delisted shadow universe is part of every relevant validation step.
- **Skipping QA.** Are we tempted to skip Stone 22 corpus QA and start ingesting? No. Dirty data poisons everything downstream.
- **Trajectory format compromise.** Is the trajectory store missing something needed for year-2 SFT? Fix in Phase 2, not later.
- **Architecture drift.** Is real data forcing changes to the Phase-1-NEW-trained architecture? If yes, pause and investigate — the toy was supposed to exercise this. Architecture changes here mean the toy missed something; document the gap in DECISIONS.md before changing the architecture.
- **Baseline observable creep.** Is the Market-State Baseline being fed non-headline-observable inputs (anything beyond rates, vol, FX, commodities) to "improve its accuracy"? No. The Baseline's input set defines its domain of operation; broadening it blurs the attribution layer. If real data has a candidate observable that's borderline, document the decision in DECISIONS.md before adding.

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
- **Full logging** — every input, forecast, calibrated forecast, action, realized return, score in the trajectory store with full provenance.
- **Calibration diagnostics dashboard** — daily reliability diagram, Brier rolling average, per-signal-class reliability table, process-quality flag, incremental AI edge over Baseline.
- **No Michael comparison.** Agent's outputs are scored only against realized returns. (DESIGN.md #10.)

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

- System has measurable incremental AI edge over the Market-State Baseline (Track C) on at least one decision class, after costs and capacity adjustment.
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
