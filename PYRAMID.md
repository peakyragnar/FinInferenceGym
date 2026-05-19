# The Pyramid

The running teaching index for FinInferenceGym. Each conceptual stone the build rests on has a short distilled summary here — the key concept, the load-bearing properties, and the "watch out for" notes. **Teaching itself happens in chat**, with full examples, counter-examples, and back-and-forth. The summary in this file is written *after* the concept is confirmed, so a future session can rebuild context in a few minutes rather than re-read the whole teaching transcript.

This file is read at session start (per CLAUDE.md). Future sessions pick up the teaching state from here — Michael does not re-teach the foundation each context window.

---

## How this document grows

Cadence per stone:

1. **Teach in chat.** The concept is explained in chat with plain language, concrete numbers, examples, counter-examples. Michael pushes back until it lands.
2. **Summarize here.** Once it lands, this document gets a short, distilled summary — the key concept and load-bearing properties, readable in a minute. Long-form teaching content stays in the chat transcript, not in here.
3. **Code.** The stone is implemented in `src/fingym/`.
4. **Verify.** The implementation runs and matches the worked numbers from the chat teaching.
5. **Next stone.**

This is how auditability is preserved as the build proceeds: every load-bearing piece is something Michael fully understands before it becomes code. The audit role (DESIGN.md #10, BIAS_PATTERNS.md) cannot function if any layer is opaque.

If Claude reverts to "write the full teaching into this file instead of chat" or "build first, summarize after," Michael names it and the cadence resets.

---

## The pyramid

The system is built up in layers. Each layer rests on the one below. A wrong layer poisons everything above it.

```
                                          [Year-2 own-model fine-tune]
                                  [Population of agents + promotion gate]
                                       [Live operation + memory]
                                  [Model-driven agent on raw evidence]
                          [Point-in-time data spine + raw-evidence channel]
                      [Evaluator validated on toys w/ adversarial agents]
                    [The evaluator's math: scoring rules + calibration]   ← starting next
                  [The atom of inference: belief, outcome, score]   ← Stones 1–7 taught
            [INFRASTRUCTURE: uv, mypy, pre-commit, Neon, alembic]   ← built (Phase 0 substeps 1–2)
```

**Infrastructure** (below the pyramid line) is not part of the project itself — it is the ground the pyramid stands on. Tooling gate (mypy strict, ruff, custom design lints, pre-commit), data substrate (Postgres 17 on Neon, alembic migrations), and the mechanism layer that enforces DESIGN.md at the code level. Built in Phase 0 substeps 1–2.

**Current position:** Layers 1, 2, and 3 complete — **Phase 0 closed 2026-05-16** (all 8 substeps green, all 4 exit criteria met, phase-gate audit passed). Stones 1–7 (atom of inference), 8–11 (excluding 11a) and 12–14 (evaluator's math), 15 (the synthetic-market toy in `src/fingym/toys/synthetic_market.py`), 16–18 (adversarial agents + ranking lock + reliability diagrams), 19 (Contract Protocol + validator + stub agent), 20 (memory artifact schema + illustrative L3 sample), 21 (property tests for math invariants) all taught, distilled, and code-verified through Phase 0. The **Constitution v5 reformulation** (2026-05-18, see [DECISIONS.md "Constitution tightening v5"](DECISIONS.md) and [CONSTITUTION_V5_PLAN.md](CONSTITUTION_V5_PLAN.md)) removed Stones 7a (four-thing decomposition), 11a (market-delta scoring), and 31 (market-implied belief recovery). New stones 7b (atom of forecast), 11b (Forecast Ledger), 11c (calibration shrinkage), 11d (Tradable-Edge Action Engine / margin of safety), 11e (Market-State Baseline) replace them. Stones 12, 13, 14, 15 survive at the concept level but their distilled summaries will be reframed under v5 vocabulary in the upcoming v5 teaching pass.

**Phase 1 NEW begins after the v5 teaching pass — Toy Architecture Extension (Weeks 3–6).** Reordered 2026-05-16 (v4) and reformulated 2026-05-18 (v5). The toy is extended *upward through the full architecture* first. Nine clusters (A–I, ~27–30 sub-stones) exercise Forecast Ledger, calibration shrinkage, Tradable-Edge Action Engine, cost models, multi-horizon scoring, PIT discipline + restatements + delisted analogs, LLM-driven agent, memory + promotion gate, population mechanic, and Market-State Baseline isolation — all in toy mode, where realized returns are emitted by the toy. Real data substitutes into the toy-trained architecture in **Phase 2 NEW** (Stones 22–28 plus real-data Stone 11e), one data type at a time. Synthetic still cannot validate alpha (per DESIGN.md "Three Arenas") — Phase 1 NEW validates every architectural property *except* alpha. See [BUILD.md Phase 1](BUILD.md#phase-1--toy-architecture-extension-weeks-36) and [PROGRESS.md](PROGRESS.md). Next: **v5 teaching pass starting from Stone 1 (quick confirm for unchanged stones) and proceeding through new stones 7b, 11b, 11c, 11d, 11e with full teach-in-chat and worked tables.** Then Phase 1 NEW Cluster A under v5 framing (single-believer toy refactor + Forecast Ledger MVP, sub-stones 11b-a through 11b-d per [PROGRESS.md](PROGRESS.md)).

---

## Table of contents — the full pyramid

The complete plan, by layer. Stones taught and committed are marked **✅**; stones below the current frontier are **⬜** and tentative — exact ordering, grouping, and count may evolve as we build. BUILD.md phases are noted in parentheses for cross-reference.

### Foundation: INFRASTRUCTURE ✅ (Phase 0, substeps 1–3)
- Tooling gate: uv, pyproject, mypy strict, ruff, custom design lints, pre-commit
- Data substrate: Neon Postgres 17, alembic baseline
- First toy in src layout: `toys/coin.py` → `src/fingym/toys/coin.py` under mypy strict

### Layer 1 — The atom of inference ✅ (Phase 0, substep 4a)
- Stone 1 ✅ — what a belief is
- Stone 2 ✅ — what an outcome is, and where time enters (with: what a label is, practically)
- Stone 3 ✅ — what "scoring a belief" means
- Stone 4 ✅ — why we grade the belief, not the outcome
- Stone 5 ✅ — what makes a scoring rule "proper"
- Stone 6 ✅ — the Brier score, formula and properties
- Stone 7 ✅ — the log score, formula and Cromwell
- Stone 7b ✅ — **the atom of forecast** (Constitution v5). Three primitives: `R_realized` (realized log return at horizon), `F_AI` (agent's forecast distribution over `R_realized`, sums to 1, no zeros), `Action` (TradeAction or NoAction). Plus the verifier-side derivation `F_AI_calibrated` (raw forecast shrunk by per-signal-class empirical reliability from the Forecast Ledger). The agent tags each forecast with a `signal_class_id` — its own categorization, searchable. Anchor: money lives in the agent's forecast only when its calibrated expected utility clears the margin-of-safety threshold AND realized return validates the side. Replaces the removed Stone 7a (four-thing decomposition). Full distilled summary in Layer 1 body below.

### Layer 2 — The evaluator's math ⬜ (Phase 0, substep 4b/4c)
- Stone 8 ✅ — calibration curves and reliability diagrams. Measures whether the agent's confidence language matches reality at scale (across many predictions, grouped by claimed confidence). Full summary in Layer 2 body below.
- Stone 9 ✅ — scoreboard assembly. A table with one row per prediction and one column per scoring metric, plus metadata columns (date, horizon, expression-type, agent_id) for slicing. Kept decomposed by default; collapsed to single numbers only at explicit decision points with declared rules. Full summary in Layer 2 body below.
- Stone 10 ✅ — multi-horizon scoring (1m / 3m / 6m / 1y in parallel; horizon set is parameterizable, not hardcoded). Same decision time produces one Contract per horizon; each scored independently. The `horizon` column on the scoreboard enables per-horizon slicing for aggregation, per-horizon held-out replay at promotion, and per-horizon domain-of-validity tagging on promoted skills. Full summary in Layer 2 body below.
- Stone 11 ✅ — expression-type tagging within `TradeAction`. Same forecast can be expressed many ways (equity-long, option-call, option-spread, vol-long, pair, etc.) with different payoff structures. The scoreboard carries `expression_type` as the broad category; specific trade details (strike, expiration, size, premium) live inside the `TradeAction` object on the Contract. Per-expression-type promotion gate. `NoAction` is a typed peer, not folded here. Full summary in Layer 2 body below.
- Stone 11b ✅ — **Forecast Ledger** (Constitution v5). Append-only record of every (forecast, realized bucket) pair indexed by signal class. Per-signal-class empirical reliability computed over many forecasts: "when this agent claimed X% confidence on bucket B in signal class Y, what fraction of those claims realized B?" Replaces the removed Stone 11a (market-delta scoring). MVP at `src/fingym/ledger/forecast_ledger.py` (in-memory, append-only); read API `reliability_for_signal_class` returns per-claim-bucket (avg claim, observed rate, count). Real-data version (Phase 2 NEW) is a Postgres view over `forecasts` + `realized_returns` — same read API. Full distilled summary in Layer 2 body below.
- Stone 11c ✅ — **Calibration shrinkage** (Constitution v5). Rewrites the agent's raw forecast `F_AI` toward per-signal-class empirical reliability from the Forecast Ledger via a sample-size-weighted blend: `shrunk = (n × empirical + k × raw) / (n + k)` where `n` is the Ledger sample size in the matching claim bin and `k` is operator-tunable `prior_strength`. Empty Ledger = identity (raw passes through). Dense Ledger = empirical overwrites raw. Applied bin-by-bin to the 5-bucket forecast, then renormalized. `F_AI_calibrated` is the only thing the action gate sees; raw is preserved for audit. Full distilled summary in Layer 2 body below.
- Stone 11d ✅ — **Tradable-Edge Action Engine / margin-of-safety gate** (Constitution v5). Calibrated expected utility under Kelly given `F_AI_calibrated` and the cost model. The signed scalar `tradable_edge_score = calibrated_expected_utility − margin_of_safety_threshold` is the gate verdict: positive → trade; non-positive → NoAction. Full distilled summary in Layer 2 body below.
- Stone 11e ⬜ — **Market-State Baseline (Track C) isolation** (Constitution v5). Separate `src/fingym/baseline/` module reads only headline observables (rates, vol, FX, commodities) and emits its own forecast distribution. Code-level isolation: `agents/` cannot import from `baseline/`. The Baseline's processed forecast is never seen by the AI Core; the audit layer computes `incremental_AI_edge = AI realized edge − Baseline realized edge` as an attribution column. Full summary lands when taught.
- Stone 12 ✅ — process-quality flag (narrow form). Single mechanical check per update: was there an emission (transcript, filing, fundamental release, news event) with `as_known` in the time window before this update? If yes, `motivated`. If no, `unmotivated` — agent updated with nothing new in the world to react to. Per-agent aggregate `unmotivated_update_rate`; promotion gate caps it (initial value: 10%). Survives Constitution v5 at the concept level; the body summary will be reframed under v5 vocabulary in the upcoming teaching pass.
- Stone 13 ✅ — decision-quality with `NoAction` as first-class peer. Coherence checks on the agent's action against the inputs (forecast, calibrated expected utility, margin-of-safety threshold, costs). Survives Constitution v5 at the concept level; the v5 reformulation changes the coherence math from "gap > cost" to "tradable_edge_score > 0," and the body summary will be reframed in the upcoming teaching pass.
- Stone 14 ✅ — **capacity-adjusted realized return** (Constitution v5). Per-Contract `realized_edge = nominal_payoff − spread − commission − market_impact(size, ADV) − alpha_decay`, where `nominal_payoff = realized_return × direction × notional` (backward-looking — the actual cash P&L before frictions, distinct from Stone 11d's forward-looking `calibrated_expected_utility`). Square-root impact law (`impact ∝ sqrt(size / ADV)`). NoAction Contracts carry `realized_edge = 0`. Sliced primarily by **deployable size bucket**; one near-tautological structural check: mean realized_edge at the agent's stated size must be `> 0` across many trades. Full distilled summary in Layer 2 body below.

### Layer 3 — Evaluator validated on toys ✅ (Phase 0, substeps 5–8)
- Stone 15 ✅ — the synthetic-market toy. Lives at `src/fingym/toys/synthetic_market.py` under mypy strict. Built originally in Phase 0 as a 3-state two-believer toy with `belief_delta_on_truth` scoring (pre-v5 framing). The Constitution v5 cleanup pass removed the two-believer setup, the `belief_delta_on_truth` scoring function, and the `STONE_11A_*` prior constants. The single-believer skeleton survives. The v5 single-believer-over-realized-returns refactor and Forecast Ledger MVP are the first deliverable of Phase 1 NEW Cluster A; the v5 distilled summary will replace this entry as Cluster A lands.
- Stone 16 ✅ — adversarial agents (ConfidentAgent, UniformAgent, BayesianAgent) implementing the typed `Agent` Protocol in `src/fingym/toys/adversarial_agents.py`. Three concrete failure modes (overconfident-wrong / no-discrimination / well-calibrated) prove the evaluator distinguishes belief quality, not just point-estimates.
- Stone 17 ✅ — validating the evaluator ranks the adversaries correctly on every scoreboard dimension. Five integration tests in `tests/integration/test_evaluator_ranks_adversaries.py` aggregate 100 episodes; mean Brier across agents satisfies BayesianAgent (0.073) << UniformAgent (0.667 exactly by symmetry) << ConfidentAgent (1.225).
- Stone 18 ✅ — reliability diagrams as visual artifacts; the Phase 0 visual exit criterion. `src/fingym/toys/reliability_diagrams.py` renders self-contained plotly HTML at `notebooks/reliability_diagrams.html`. ConfidentAgent shows overconfidence; UniformAgent shows zero discrimination; BayesianAgent tracks the diagonal. Structural-shape tests in `tests/integration/test_reliability_diagrams.py`.
- Stone 19 ✅ — the model interface contract. Pydantic `Contract` with 11 nested types in `src/fingym/agents/contract.py`; PEP 695 generic `Agent[Evidence]` Protocol in `src/fingym/agents/interface.py`; six Phase 0 validation checks in `src/fingym/agents/contract_validator.py`; `BayesianContractEmitter` stub in `src/fingym/toys/contract_emitter.py` proves the Protocol compiles.
- Stone 20 ✅ — the memory artifact schema. Pydantic `MemoryArtifact` for L2/L3 per memory-design.md in `src/fingym/memory/schema.py` (7 nested types; L3 invariant enforced via `model_validator`); illustrative L3 sample in `memory_registry/promoted/`. Scaffolding for Layer 7.
- Stone 21 ✅ — property tests for math invariants. Hypothesis-based tests in `tests/property/test_math_invariants.py`: Bayesian update commutativity (coin + 3-state), Brier and log_score properness in expectation, reliability_buckets count invariant, Brier-zero-on-degenerate-correct. The pre-v5 `belief_delta` property tests were removed by the v5 cleanup pass alongside the `belief_delta_on_truth` function.

> *Phase 0 exit ✅ — closed 2026-05-16. Final-state metrics: 92 unit + 10 integration + 8 property + 22 lint = 132 tests green; mypy strict clean across 31 source files. See [PROGRESS.md "Completed Phases"](PROGRESS.md#completed-phases) for the full close-out summary.*

### Layer 4 — Point-in-time data spine + raw-evidence channel ⬜ (Phase 2 NEW)
> Reordered 2026-05-16. Was Phase 1; now Phase 2 NEW after Phase 1 reorder. Some elements (PIT discipline, restatement events, delisted analogs) are first exercised in toy mode in Phase 1 NEW Cluster E, then on real data here.

- Stone 22 ⬜ — corpus QA (validate the existing 10-year / 1700-name transcript corpus before any data flows). **First real-data step in Phase 2 NEW.**
- Stone 23 ⬜ — the six data types in the canonical schema (emissions, derived_evidence, forecasts, actions, realized_returns, scores) plus headline_observables and the Forecast Ledger view — derived_evidence is mechanical transformation only, never alpha cognition
- Stone 24 ✅ (toy mechanism) — **point-in-time discipline** (`as_of` vs `as_known`, restatements, look-ahead audits). Two timestamps per record; the `time_leak_guard(records, query_tick)` function is the single mechanism. Toy mechanism distilled in Phase 1 NEW Cluster E (full distilled summary in Layer 4 body below). Real-data version is Phase 2 NEW: substitute real vendor `as_known` timestamps into the same plumbing.
- Stone 25 ⬜ — replay vs live parity (the same pipeline must run both, byte-identical)
- Stone 26 ✅ (toy mechanism) — **survivorship and the delisted shadow universe.** Delisted companies stay in the universe with a well-defined post-delist `realized_return`; the Scoreboard never silently drops them. Toy mechanism distilled in Phase 1 NEW Cluster E (full distilled summary in Layer 4 body below). Real vendor: SEC EDGAR cross-reference for delisted CIKs (FMP/Massive don't cover pre-2024). Phase 2 NEW substitutes real corporate-action feeds.
- Stone 27 ⬜ — the trajectory store as year-2 SFT fuel (every forecast / action / realized return / score preserved in SFT-fit format). **Schema instantiated in toy mode at Phase 1 NEW; migrated to real v5 Contracts here.**
- Stone 28 ⬜ — the raw-evidence channel (typed pipe delivering full unprocessed evidence to a model on demand)

### Layer 5 — Model-driven agent on raw evidence ⬜ (Phase 1 NEW + Phase 2 NEW)
> Reordered 2026-05-16. Stones 30, 31, 32 are first instantiated in toy mode in Phase 1 NEW (Clusters F, A, B respectively). Stone 29 (pure-code plumbing baseline) is largely absorbed by Phase 1 NEW Cluster F — kept here in case real-data substitution exposes plumbing-only validation needs.

- Stone 29 ⬜ — the pure-code plumbing baseline (hand-coded Bayesian — validates the pipeline, never promoted). Likely absorbed by Phase 1 NEW; revisit at Phase 2 NEW if needed.
- Stone 30 ✅ (toy instantiation) — **the first model-driven agent.** Raw emission stream in (wrapped as natural-language signals); structured forecast distribution + self-applied `signal_class_id` out via tool-call output. Model swap (DESIGN.md #7): the agent depends on a typed `ForecastClient` Protocol, not on any specific provider SDK. First instantiation distilled in Phase 1 NEW Cluster F using Claude Haiku 4.5 (full distilled summary in Layer 5 body below). On real data in Phase 2 NEW (substitutes real filings / transcripts for toy emissions in the same prompt-and-Protocol path).
- Stone 33 ⬜ — fractional Kelly sizing (0.25× to 0.5× Kelly for miscalibration absorption). Under v5, Kelly is applied to `F_AI_calibrated` (the calibration-shrunk forecast) inside the Tradable-Edge Action Engine (Stone 11d). Touched in Phase 1 NEW Cluster B.

### Layer 6 — Live operation + memory ⬜ (Phase 3)
- Stone 34 ⬜ — live-feed engineering (market hours, halts, outage handling without info leak)
- Stone 35 ⬜ — memory artifact lifecycle (proposed → probationary → promoted → retired)
- Stone 36 ⬜ — calibration diagnostics dashboard (live reliability diagram, Brier rolling average)
- Stone 37 ⬜ — no-Michael-comparison enforcement at the live layer (DESIGN.md #10 made structural)

### Layer 7 — Population + promotion gate ⬜ (Phase 1 NEW + Phase 4)
> Reordered 2026-05-16. The MECHANISMS of population (Stone 38), proposal (Stone 39), and the promotion gate (Stone 40) are first exercised in toy mode in Phase 1 NEW Clusters G and H. Real-evidence promotion is Phase 4.

- Stone 38 ✅ (toy mechanism) — **population variants.** ≥3 `LlmAgentVariant` configurations run in parallel on the same emission stream; each variant produces its own slice of the Scoreboard distinguished by `agent_id`. Cluster H mix: 2× Haiku (different prompts) + 1× Sonnet. Variants are operator-controlled; tags are model-controlled — the cross-model check (Stone 40 check 2) counts variants where a tag is high-signal. Toy mechanism distilled in Phase 1 NEW Cluster H (body in Layer 7 below). Real-data version is Phase 2 NEW (with more axes — temperature, additional architectures, memory-subset variants).
- Stone 39 ✅ (toy mechanism) — **LLM as proposer of candidate memory items.** The model emits a `propose_memory_item(content, signal_class_id, horizons)` tool call OPTIONALLY alongside `submit_forecast`. Most calls don't propose anything; the model proposes only when it sees a generalizable pattern. Toy mechanism distilled in Phase 1 NEW Cluster G (body in Layer 7 below). Real-data version is Phase 2 NEW.
- Stone 40 ✅ (toy mechanism — Clusters G + H) — **the four-check promotion gate.** After Cluster H: checks 1 (held-out replay; per-variant), 2 (cross-model regression; ≥2 of 3 variants confirm), and 4 (domain-of-validity declared) wired up with real evaluation. Check 3 (survivorship) still stubbed `passed=False`; real check 3 lands in Phase 2 NEW. L2 tier is real (`memory_registry/probationary/<id>.yaml`); re-validation runs every 50 new Scoreboard rows; L3 ↔ L2 ↔ retired transitions all flow through it. Toy mechanism distilled in Phase 1 NEW Clusters G + H (body in Layer 7 below).
- Stone 41 ⬜ — Goodhart resistance via scoreboard composition (a memory item that improves only one metric is suspect)

### Apex — Year-2 own-model fine-tune ⬜ (Phase 5)
- Stone 42 ⬜ — cross-model swap test (≥2 frontier + ≥1 open-weights; promoted memory must survive)
- Stone 43 ⬜ — SFT data preparation from the trajectory store; sample fine-tune on a small open-weights model
- Stone 44 ⬜ — capacity-adjusted scoring with realistic retail market-impact assumptions
- Stone 45 ⬜ — the year-2 plan document (data accumulation targets, fine-tune triggers, deployment criteria)

---

## Layer 1 — The atom of inference

The smallest unit of the entire project. Every higher layer is a variation on the same shape:

> A **belief** is formed about the world. Later, an **outcome** is revealed. The belief is **scored** against the outcome.

Three primitives — belief, outcome, score. From these three, the whole gym grows.

### Stone 1 — what a belief is

A **belief** is a probability distribution over a fixed set of hypotheses: a small table where the rows are the possible worlds, the values are non-negative numbers, and the values sum to exactly 1.

```
Hypothesis  Probability
fair        0.30
biased      0.70
```

That table is the entire data structure the agent emits when forming a belief. Model produces it. Evaluator scores it. Promotion gate compares it. Every other piece of the system reads beliefs in this shape.

Load-bearing properties to remember:

- A belief is never a single guess. "I think it's biased" isn't a belief; `{fair: 0.30, biased: 0.70}` is.
- A belief contains uncertainty by construction. `{0.5, 0.5}` means "no information" — a legitimate belief, not a non-answer.
- Confidence ≠ correctness. A 99% confident belief can be wildly wrong; a 50/50 belief can land on the right side by luck. Scored separately.
- Probability 0 is structurally dangerous: it says "logically impossible," and Bayes cannot recover from it. Returns in Stone 7 (Cromwell).

### Stone 2 — what an outcome is, and where time enters

An **outcome** is the truth, revealed later: exactly one hypothesis from the belief's set, revealed at `t_outcome > t_belief`. The agent does not see it when forming the belief.

The **time asymmetry** between the agent's info (knowable at `t_belief`) and the evaluator's info (the agent's info PLUS the outcome at `t_outcome`) is the foundation of evaluation. Without it, the agent could read the answer key and trivially score 100%; evaluation would mean nothing.

Two engineering principles fall out:

1. **Point-in-time discipline (DESIGN.md #3).** Every fact carries `as_of` and `as_known` timestamps so an agent reasoning about a past date cannot see future revisions. The Postgres schema we set up in substep 2 is the mechanism.
2. **Time-revealed labels only (DESIGN.md #10).** Outcomes come from the world later, never from Michael's judgment, never from narrative. No human-labeled training data.

In finance, future emissions used as proxies for state (next-quarter revenue, future earnings revisions) are themselves hypotheses about how state translates to emission — Stone 4 returns to why this matters.

#### What a label is, practically

An **outcome** is what happens in the world. A **label** is a row in the `labels` table — the recorded, time-stamped piece of data the evaluator uses as the outcome for scoring. The mapping isn't always 1:1.

- **Toy case (coin):** label = outcome. Open the box, see `"biased"`, store the row.
- **Real case (company):** the realized return at horizon is never observable at decision time. The label is **constructed** from future price + corporate actions + payoff structure via a labelling function we have to design. That function has model assumptions baked in — which horizon, simple vs log returns, expression-specific payoff for options/vol/pairs. **Good labelling functions are a real research direction in this project, not a free input.** A wrong labelling function makes the evaluator fake.

Every label row carries: `label_value`, `belief_id` link, `horizon`, `as_known`, `source`, and a `version` for when restatements update the underlying observable.

**One belief → many labels.** A single belief gets scored at multiple horizons in parallel (1m / 3m / 6m / 1y), each with its own labelling-function output and its own `as_known`. The evaluator produces a score per horizon. Discovering at which horizon an agent has edge is empirical, not pre-committed (DESIGN.md "Multi-horizon scoring").

### Stone 3 — what "scoring a belief" means

A scoring function has signature `score(belief, label) → number`. Both inputs required. Returns a single real number. By convention: **lower is better** (a loss). Zero would be perfect; positive is some amount of wrongness.

Three required properties — each prevents a specific failure mode:

- **Deterministic.** Same belief + same label → same number, every time. A noisy scorer would jitter agent rankings and hide skill below the noise floor; you couldn't tell two analysts apart whose skill gap is below the scorer's noise. The scoring layer must be silent on uncertainty so all observed uncertainty is the agent's.
- **Pure.** No external state read or written. An impure scorer (e.g., one that reads a hidden "regime multiplier") is a vector for silent bias-import: someone can change the dependency and retroactively shift every agent's grade, and the mechanism layer can't catch what's not in the function's source.
- **Lives on the verification side.** The agent never imports or calls the scoring function on its own work (DESIGN.md #5). If it could, it would optimize directly against the metric, silently revise beliefs that would score badly, or — worst case — read the label and emit a perfect belief. Once agents exist, `src/fingym/agents/` will be structurally forbidden from importing `src/fingym/evaluator/` via import-linter.

**Why one number per row.** Every aggregation the evaluator does — mean across calls (agent's grade), bucketing by claimed confidence (calibration curve), per-horizon / per-expression slicing, agent comparisons — requires a single comparable number per `(belief, label)` row.

**Scoreboard reconciliation.** DESIGN.md "scoreboard, not scalar" means *multiple* scoring functions in parallel (Brier + log score + calibration error + decision-quality + ...). Each obeys this Stone 3 signature individually; the scoreboard is the vector across functions per row, then aggregated per column. Diversity across columns is what catches failure modes any single number would miss.

In the code: `brier[H](belief: dict[H, float], outcome: H) -> float` and `log_score[H](belief: dict[H, float], outcome: H) -> float` in `src/fingym/evaluator/scoring.py` are concrete instances of this signature. The parameter is called `outcome` in current code; it carries the `label_value` from a label row. Stones 6 and 7 will explain *why those specific formulas.*

### Stone 4 — why we grade the belief, not the outcome

The choice: grade the whole belief distribution, or grade just "did the agent put the highest probability on the side that won?" These produce **opposite** incentive structures.

**Outcome-grading collapses calibrated and bluffer.** Two agents with the same hit rate (e.g., 7/10) look identical under outcome-grading — the 70/30 calibrated analyst and the always-99/1 bluffer score the same. The math literally discards the distribution information needed to tell skill from confidence.

**Outcome-grading rewards bluffing as the optimal strategy.** Right at 99% scores the same as right at 60%, so the "extra 39% confidence" is free. The agent learns to max-confidence on whichever side it thinks more likely.

**Belief-grading + asymmetric punishment fixes this.** Brier (squaring) and log score punish probability on the wrong side disproportionately. Confidently-wrong costs *much* more than calibrated-wrong. Worked example with both agents at 7/10 hit rate: bluffer averages Brier ≈ 0.59; calibrated 70/30 agent averages ≈ 0.42. They diverge sharply.

**This is THE deepest commitment in the project.** Outcome-grading → guessing system, overconfidence wins. (Proper) belief-grading → learning system, honest calibration wins. Everything downstream — calibration, proper scoring, scoreboard diversity, population search, verified promotion — flows from this choice.

**Why finance defaults to outcome-grading.** Low manager prediction frequency × short evaluation windows × no belief recording infrastructure = too few samples to belief-grade. Our architecture (~1700 names × 4 horizons × continuous belief updates × data-spine recording) sidesteps all three. **Horizon length is NOT the relevant variable** — sample count is. Shorter per-prediction horizons would only accelerate sample accumulation; we'd still belief-grade.

**Steelman.** Outcomes are what compound. Calibration alone is academic; Kelly sizing alone is destructive (oversizes miscalibrated edges). It's calibration + fractional Kelly together that turn inference quality into compound returns. We grade the cause (calibration); compounding turns it into the consequence (log-wealth growth).

### Stone 5 — what makes a scoring rule "proper"

Belief-grading alone isn't enough: some belief-graders still reward bluffing (e.g., linear scoring `S = −belief[outcome]`). The subset of belief-graders that doesn't is called **proper**.

**Proper property.** A scoring rule is proper if, for any true belief `q`, the agent's expected loss is **uniquely minimized by reporting `r = q`**. Honest reporting is the dominant strategy. The rule literally shapes what the agent learns to do.

**Shape difference — visible in a spreadsheet.** Plot expected loss vs reported `r` while holding the true probability `q` fixed:

- **Linear** (improper): straight downhill line. Optimum at the extreme (`r → 1`). Rewards bluffing.
- **Brier** (proper): U-shaped valley with minimum at `r = q`.
- **Log score** (proper): U-shaped valley with minimum at `r = q`, steeper walls at the extremes.

The U-shape exists because Brier and log score punish confident-wrong **disproportionately** to the reward for confident-right. Above `r = q`, the marginal cost of going more extreme outpaces the marginal gain.

**Why the squaring/log shapes specifically:**
- **Brier** = `Σ_h (belief[h] − 1[h==outcome])²`. The square is what asymmetrically punishes confident-wrong vs rewards confident-right.
- **Log score** = `−ln(belief[outcome])`. The log is what makes the punishment grow without bound as the probability on the truth approaches zero.

**Brier vs log score — different shapes of punishment:**
- **Brier**: bounded. Max loss ≈ 2 for binary. Confident-wrong tops out around 1.96 — doesn't explode.
- **Log score**: unbounded. Approaches `+∞` as probability on the truth approaches 0.

**Cromwell and near-Cromwell.** Cromwell's rule: never assign probability exactly 0 to anything not logically certain. Bayesian updating multiplies prior × likelihood; if the prior is 0, the posterior is 0 forever — the hypothesis is unrecoverably ruled out. A **Cromwell failure** is assigning `p = 0` on the truth. A **near-Cromwell failure** is the same shape with very-small-but-nonzero probability (e.g., `p = 0.001`): log score = 6.91; Brier = 1.996. **Log score is the smoke alarm; Brier shrugs.** The Asymmetry of Ruin (intuitions.md #12) makes near-Cromwell structurally dangerous once positions are sized.

**Why both on the scoreboard.** Brier averages politely across many calls (catches general miscalibration). Log score screams at one bad row (catches near-Cromwell). An agent's mean Brier can look fine while one near-Cromwell row pulls the mean log score visibly upward — flagging a hidden disaster the Brier average smoothed over. Running both means catching what either alone would miss.

**Don't combine routinely.** Each scoring function is its own column on the scoreboard. Aggregations happen per column (mean Brier, mean log score, …). Composition into a single number happens **only at explicit decision points with declared rules** (e.g., "promote a memory item if Brier improves AND log score doesn't worsen"). Per DESIGN.md: scoreboard, not scalar. Routine collapse hides failure modes; explicit collapse at a decision point keeps the components visible.

### Stone 6 — the Brier score, formula and properties

**Formula:**

```
Brier(belief, outcome) = Σ_h (belief[h] − 1[h == outcome])²
```

For each hypothesis, take the probability the agent assigned, subtract 1 if that hypothesis is the actual outcome (0 otherwise), square it, sum across all hypotheses.

**Coin example.** Belief `{fair: 0.30, biased: 0.70}`, outcome `"biased"`:
- For `fair`: `(0.30 − 0)² = 0.09`
- For `biased`: `(0.70 − 1)² = 0.09`
- Sum: **0.18**

**Why proper.** Expected Brier `E[Brier | r] = q × 2(1−r)² + (1−q) × 2r²` is a quadratic in r with its unique minimum at `r = q`. Derivative: `−4q + 4r = 0 → r = q`. The valley always lands at the truth, regardless of `q`.

**Edge cases:**
- Max loss: **2.0** for binary (and any K). **Bounded** — never blows up.
- Min loss: 0.0 (100% on the truth).
- Cromwell case (p=0 on the truth): contributes 2.0. Loud but finite. Doesn't dominate averages the way log score does.

**In code.** `src/fingym/evaluator/scoring.py:brier()`. The `for` loop is `Σ_h`; `indicator = 1.0 if hypothesis == outcome else 0.0` is the indicator function; degenerate case (outcome not in belief's support) adds 1.0 as a full-miss penalty.

**Pairs with log score (Stone 7).** Brier is bounded → averages politely across many calls, doesn't scream at near-Cromwell. Log score is unbounded → screams. Running both catches general miscalibration AND catastrophic overconfidence.

### Stone 7 — the log score, formula and Cromwell

**Formula:**

```
log_score(belief, outcome) = −ln(belief[outcome])
```

Take the probability the agent assigned to the actual outcome, take its natural log, flip the sign. Only `belief[outcome]` from the distribution matters; everything else is ignored.

**Coin example.** Belief `{fair: 0.30, biased: 0.70}`, outcome `"biased"`:
- log_score = `−ln(0.70) ≈ 0.3567`

**Why proper.** Expected log score `E = −q ln(r) − (1−q) ln(1−r)` is U-shaped (convex) in r with unique minimum at `r = q`. Derivative `−q/r + (1−q)/(1−r) = 0 → r = q`. Same proper property as Brier; different curve shape.

**The Cromwell mechanism — built-in infinite penalty:**

- `ln(0) = −∞` → `−ln(0) = +∞`.
- Agent assigned probability 0 to the actual outcome → log score = `+∞`. **Literally infinite, not "very bad."**
- This is intentional: the math refuses to forgive an unrecoverable Bayesian failure. A probability-0 hypothesis cannot be resurrected by any future evidence; the log score forces that unrecoverability into the loss.
- Smooth approach to infinity (catches *near*-Cromwell, not just exact zero):
  - `p = 0.10` → loss 2.30
  - `p = 0.01` → loss 4.61
  - `p = 0.001` → loss 6.91
  - `p = 0` → loss `+∞`

**Edge cases:**

- Min loss: 0.0 (probability 1 on the truth).
- Max loss: **unbounded**.
- One row of `+∞` makes any mean `+∞`. Operational handling: count Cromwell violations separately, average only over non-violation rows. `+∞` IS the signal, not an average input.

**In code.** `src/fingym/evaluator/scoring.py:log_score()`. `belief.get(outcome, 0.0)` pulls the probability; returns `math.inf` if zero-or-missing; otherwise `−math.log(probability)`. The `math.inf` IS the Cromwell signal — downstream code is responsible for handling it loudly.

**Brier vs log score, side by side:**

| Property | Brier | log score |
|---|---|---|
| Inputs used | whole distribution | only `belief[outcome]` |
| Max loss | 2.0 (bounded) | `+∞` (unbounded) |
| At Cromwell | 2.0 | `+∞` |
| Averaging | smooth | one bad row dominates |
| Best for | general miscalibration | near-Cromwell detection |

Both proper. Both reward `r = q`. Run both — different failure modes surface in different columns.

---

### Stone 7b — the atom of forecast (Constitution v5)

The atom Layer 2 operates on. Replaces the removed Stone 7a (four-thing decomposition). Under v5 the agent forecasts realized returns directly; no hidden state to categorize; no market belief to recover.

**Three primitives.**

| Symbol | What it is | When known |
|---|---|---|
| `R_realized` | The realized log return for the (name, horizon, expression-type). One number — e.g., `+6.4%` log. | Revealed at horizon. Hidden at decision time. |
| `F_AI(R)` | The agent's forecast distribution over `R_realized`. A small table of (return bucket → probability). Sums to 1. No bucket assigned 0 (Cromwell). | Emitted at decision time. |
| `Action` | The chosen action. Typed sum: `TradeAction(...)` or `NoAction`. Peers, not sub-types. | Emitted at decision time. |

Plus the **verifier-side derivation** (computed by the Action Engine, not the agent):

| Symbol | What it is | When computed |
|---|---|---|
| `F_AI_calibrated` | Raw `F_AI` shrunk toward per-signal-class empirical reliability from the Forecast Ledger | At decision time, after the agent emits `F_AI` |

**Signal class — the agent's categorization.** Every forecast is tagged with `signal_class_id` — the agent's own name for what kind of forecast it is. The Forecast Ledger groups forecasts by signal class and tracks empirical reliability per class over many forecasts. Examples: `mid_cap_tech_margin_surprise_q3`, `commodity_supply_shock_3m_equity_long`, `cfo_qualifier_density_q3_post_2020` (the last has no Wall Street analog — the agent invents categorizations as it discovers them). Signal classes are **searchable** under DESIGN.md — the agent proposes; the Ledger tracks; new classes emerge from cognition without architectural change.

**The anchor sentence.**

> Money lives in the agent's forecast only when its calibrated expected utility (computed under `F_AI_calibrated` and the cost model) clears the margin-of-safety threshold, AND the realized return `R_realized` validates the side the agent took.

Four conditions, all required:
1. **Discriminating.** `F_AI` is non-uniform (not a hedge).
2. **Reliable.** Signal class has accumulated empirical reliability in the Ledger.
3. **Clears the gate.** Calibrated expected utility under `F_AI_calibrated` exceeds margin-of-safety after costs (Stone 11d).
4. **Validated.** `R_realized` falls consistently with the forecast's leaning.

If any link fails, no edge.

**What v5 removed from cognition.**

| Pre-v5 cognition load | v5 status |
|---|---|
| Categorize returns into hidden states (`S_true`) | Removed — no state ontology |
| Recover `P_market(S)` from prices/options/spreads | Removed — no inversion required |
| Compute `belief_delta = P_AI − P_market` | Removed — no gap math |

The verifier-side machinery (Forecast Ledger, calibration shrinkage, Action Engine, isolated Baseline) replaces these — but lives on the verifier side per DESIGN.md #5. **The agent's cognition load is smaller under v5, not larger.**

**Bridge to Layer 2.** Every Layer 2 stone measures one property of the atom over many forecasts:

| Stone | What it measures (over the atom) |
|---|---|
| 8 calibration | Does `F_AI` claim X% match realized rate? |
| 9 scoreboard | All metrics per Contract; columns; per-signal-class slicing |
| 10 multi-horizon | Same forecast pipeline at 1m / 3m / 6m / 1y in parallel |
| 11 expression-type | Same `F_AI` shape, different action expressions |
| 11b Forecast Ledger | Per-signal-class empirical reliability over many forecasts |
| 11c calibration shrinkage | How raw `F_AI` becomes `F_AI_calibrated` |
| 11d action engine | Calibrated expected utility + margin-of-safety gate |
| 11e Baseline isolation | Parallel control; incremental AI edge attribution |
| 12 process quality | Emission in window before this forecast? |
| 13 decision quality | Coherence of action with forecast + calibration + costs |
| 14 capacity-adjusted return | What of nominal edge survives at deployable size |

**One sentence.** Stone 7b is the atom every v5 measurement is built on — `(F_AI, signal_class_id, Action)` emitted by the agent at decision time, `(R_realized, F_AI_calibrated, final_action_verdict, score)` resolved on the verifier side — and the architecture above this stone is just "what we do with many of these tuples."

---

**Layer 1 — atom of inference — complete through Stone 7.** Belief, outcome, label, score signature, why-belief-not-outcome, properness, Brier, log score. The Layer-1 scoring functions are implemented in `src/fingym/evaluator/scoring.py` (substep 4a). Stone 7b (atom of forecast) is the v5 bridge from Layer 1 to Layer 2 and lands as a full distilled summary during the v5 teaching pass. Next: **Layer 2 — the evaluator's math** (calibration curves, scoreboard assembly, multi-horizon and expression-type aggregation, plus the Forecast Ledger, calibration shrinkage, Tradable-Edge Action Engine, and Market-State Baseline introduced by Constitution v5).

---

---

## Layer 2 — The evaluator's math

### Stone 8 — calibration curves and reliability diagrams

**The question.** When the agent says "X percent confident," does the truth actually happen X percent of the time?

This cannot be answered from any single prediction. It is a statistical property of the agent visible only across many predictions.

**The procedure — count, group, compare.** Given many predictions from one agent with their actual outcomes:

1. **Group** predictions by the claim. All predictions where the agent said ~40%. All where it said ~70%. Etc.
2. For each group, compute two numbers: **Mean claim** (what the agent said, averaged) and **Observed rate** (fraction of those predictions where the positive outcome actually happened).
3. If claim ≈ observed, the agent is calibrated for that group.
4. If claim > observed, the agent is overconfident in that group.
5. If claim < observed, the agent is underconfident in that group.

**Worked example.** Three adversarial agents, 200 binary events each (true probabilities mixed from {40%, 60%, 80%}; base rate ≈ 60%).

**Agent W (well-calibrated, says true probability):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 40-50% | 73 | 40.0% | 34.2% | 5.8 |
| 60-70% | 65 | 60.0% | 66.2% | 6.2 |
| 80-90% | 62 | 80.0% | 74.2% | 5.8 |

Calibration error: **5.9 pp**. Small gaps in every bucket — sampling noise from only 200 events. The agent is calibrated.

**Agent O (confidently-wrong, pushes claims to extremes 10% or 90%):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 10-20% | 73 | 10.0% | 34.2% | 24.2 |
| 90-100% | 127 | 90.0% | 70.1% | 19.9 |

Calibration error: **21.5 pp**. When O said 90%, reality was only 70%. When it said 10%, reality was 34%. Big gaps in both directions.

**Agent U (always-50%, ignores evidence):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 50-60% | 200 | 50.0% | 57.0% | 7.0 |

Calibration error: **7.0 pp**. One bucket. Agent has no discriminative value — it cannot distinguish a 40% event from an 80% event.

**The single-number summary (Expected Calibration Error, ECE).** Weighted average of bucket gaps: per bucket, multiply gap by # events; sum across buckets; divide by total events. One number per agent that ranks them.

**Important limitation.** ECE is a summary; the reliability table is the diagnostic. Agent U's ECE (7.0) looks similar to W's (5.9), but U's single-bucket structure gives the game away. **Calibration alone is necessary, not sufficient.** Combine with Layer-1 scoring rules (Brier, log score) to catch uninformative agents that have low ECE by accident.

**The three classic signatures:**

| Signature | What the table shows | Reading |
|---|---|---|
| Calibrated | Many buckets, claim ≈ observed each row | Trustable across confidence levels |
| Overconfident | Buckets at extremes (10%, 90%) with claim much higher than observed | When agent says 90%, treat it as ~70% |
| Underconfident | Buckets where claim < observed | Agent is hedging; could have claimed more |
| Uninformative | One bucket only; observed ≈ base rate | Useless even if ECE is low |

**Connection to Layer 1.** Layer 1 scored the forecast on single predictions (Brier, log score per row). Stone 8 scores the forecast across many predictions. Both are about the agent's forecast in isolation. The v5 Stones 11b/11c (Forecast Ledger + calibration shrinkage) will introduce empirical per-signal-class reliability — the verifier-side adjustment that shrinks the agent's raw forecast toward what it has historically delivered.

**Formal symbols.** Reference notation lives in [FORMULAS.md](FORMULAS.md) under "Calibration measurement (Stone 8)." Not needed for understanding; provided for code/agent reference.

### Stone 9 — scoreboard assembly

**The data structure.** The evaluator's output is a **table**. One row per prediction (one `Contract`). One column per scoring metric. Plus metadata columns for slicing — date, agent_id, horizon, expression-type, sector. Production scoreboards have many columns; the schema grows as each Layer-2 stone adds its metric.

**Example shape** (six columns shown; the real one is wider):

| Prediction ID | Date | Agent's claim | What happened | Brier | log_score |
|---|---|---|---|---:|---:|
| pred_001 | 2026-05-15 | 70% biased | biased | 0.18 | 0.36 |
| pred_002 | 2026-05-16 | 50% biased | fair | 0.50 | 0.69 |
| pred_003 | 2026-05-17 | 99% biased | biased | 0.0002 | 0.01 |
| pred_004 | 2026-05-18 | 30% biased | biased | 0.98 | 1.20 |

That's it. A spreadsheet of evaluation results.

**Why we keep it decomposed (do NOT routinely collapse to one number):**

- **Different columns catch different failure modes.** Brier catches moderate overconfidence; log score catches near-Cromwell; calibration error catches systematic skew. Each column lights up red for a different kind of failure. Averaging them washes out the signal.
- **Goodhart resistance.** A single optimization target gets gamed. Multiple parallel metrics under different proper scoring rules cannot all be gamed simultaneously without honest reporting. One column = one thing to fool; many columns = harder to fool.

**Two kinds of operations on the scoreboard:**

- **Aggregate per column.** Mean Brier across all rows. Mean log score (filtering out Cromwell rows). ECE per bucket. Count of rows where Brier < 0.1. Each aggregation is per column; columns stay separate.
- **Slice by metadata.** "Mean Brier on 6-month horizon predictions only" — filter rows by horizon, then mean. "Calibration error in tech sector vs financial sector" — filter, compute per slice. Same scoreboard, different slices answer different questions.

**When to collapse to a single number — only at specific decision points with explicit rules.** Example promotion rule:

> Promote a memory item to L3 if and only if its addition improves Brier by ≥5% AND doesn't worsen log score AND doesn't widen any calibration bucket gap by more than 3 percentage points.

That's three columns with three thresholds. The collapse rule is written down. The scoreboard itself stays decomposed. From intuitions.md #2: "Collapse to a scalar only at decision points, and make the collapse rule explicit."

**Column-on-scoreboard vs hard-cap-on-column — the default and the exception.**

When a new scoring metric is added, the default is: it becomes a **column** that the promotion gate weighs alongside other columns. A weak number on one column can be redeemed by strong numbers elsewhere; the gate is the combination rule, not any single column.

A **hard cap** (the metric must be above/below a fixed number, or the agent is rejected outright regardless of other scores) is a stronger move. It says: there is no compensating virtue for failing this metric. Reserve hard caps for the narrow case where this is genuinely true.

Two worked examples from Layer 2:

- Stone 12's `unmotivated_update_rate` — hard-capped at 0.10. There is no compensating virtue for "agent issued an update with no new evidence in the world." It's price-following structurally, and no amount of good output redeems it.
- Stone 13's `decision_quality_rate` — column, NOT a hard cap. An incoherent-looking decision can be legitimate (crowding, hedging, atypical vol pricing) because the three mechanical coherence checks don't model every real factor. The gate considers it alongside per-signal-class reliability (Forecast Ledger), calibrated expected utility, and held-out realized edge; an agent can score modestly on Stone 13 and still be the right one to promote if its other columns are strong.

The shape of the question for any new metric: "Is there ANY legitimate reason an agent might score poorly on this and still be a better agent than one that scores well?" If yes → column. If no → hard cap is on the table.

**How Stones 10–14 use this scoreboard:**

- Stone 10 (multi-horizon) — adds a `horizon` column; runs aggregations per horizon slice.
- Stone 11 (expression-type) — adds an `expression_type` column; aggregations per action type.
- Stones 11b–11e (v5) — add `signal_class_id`, per-signal-class reliability, `calibrated_expected_utility`, `tradable_edge_score`, and `incremental_AI_edge` columns.
- Stones 12, 13, 14 — each add their column.

The scoreboard schema is locked at the structural level here; columns grow as each stone lands.

**Connection to memory architecture.** Scoreboard rows are L0 trajectory records (see [memory-design.md](memory-design.md)). Immutable, append-only, point-in-time. Aggregations are computed *from* the immutable rows; no row is ever updated in place.

**In code.** Schema lives in `src/fingym/evaluator/scoreboard.py` (Phase 0 substep 4b/4c deliverable). Row construction at evaluation time; aggregations and slicing performed by the evaluator's reporting layer.

**One sentence.** The scoreboard is a table — one row per prediction, one column per scoring metric, plus metadata columns for slicing. Decomposed by default. Collapse only at explicit decision points with declared rules.

### Stone 10 — multi-horizon scoring

**The reframe.** "What is the realized return?" is an incomplete question. The complete question is **"what is the realized return, over this time window?"** A 1-month realized return (cyclic dynamics) and a 1-year realized return (strategic positioning) are different claims about different things.

**The mechanic.** A single decision-time produces multiple `Contract` objects — one per horizon the agent cares about. Each gets its own row in the scoreboard, distinguished by the `horizon` column.

Example: agent's beliefs about AAPL at 2026-05-15:

| Decision time | Company | Horizon | P_AI(strengthening) | Scored against |
|---|---|---|---:|---|
| 2026-05-15 | AAPL | 1m | 60% | AAPL's state at 2026-06-15 |
| 2026-05-15 | AAPL | 3m | 55% | AAPL's state at 2026-08-15 |
| 2026-05-15 | AAPL | 6m | 40% | AAPL's state at 2026-11-15 |
| 2026-05-15 | AAPL | 1y | 30% | AAPL's state at 2027-05-15 |

Four rows. Same agent. Same company. Same decision time. Four different futures to score against.

**The discovered fact.** After running over time, the scoreboard's horizon slices tell you where each agent's edge lives:

| Per-horizon performance | Brier | log_score | Calibration error |
|---|---:|---:|---:|
| 1m | 0.18 | 0.32 | 4 pp |
| 3m | 0.21 | 0.40 | 6 pp |
| 6m | 0.35 | 0.65 | 14 pp |
| 1y | 0.42 | 0.85 | 22 pp |

This agent is sharp at short horizons and degrades at long ones. That's a discovered fact, not a pre-commitment. The system never pre-commits to "we are a quarterly system" or "we are a year-horizon system." It discovers per-agent, per-sector, per-skill where edge actually lives. (DESIGN.md "Operational Constraints" — multi-horizon scoring.)

**Per-horizon promotion gate.** The four-check promotion gate (DESIGN.md #4) runs **per horizon, independently.** A candidate skill is promoted with `horizon: [list]` in its domain-of-validity listing the specific horizons where all four checks passed:

| Check at horizon | 1m | 3m | 6m | 1y |
|---|:---:|:---:|:---:|:---:|
| Held-out calibration improves | ✓ | ✓ | ✓ | ✗ |
| Cross-model (≥2 engines) | ✓ | ✓ | ✓ | (n/a) |
| Survivorship check | ✓ | ✓ | ✓ | (n/a) |

→ Promoted with `horizon: [1m, 3m, 6m]`. **Excluded from 1y context** by the domain-of-validity filter. At inference time, an agent operating at 1y horizon never sees this skill.

This is what prevents the "skill that worked at 3m leaks into 1y and corrupts long-horizon calls" failure mode. The horizon column on the scoreboard is what enables both per-horizon promotion testing and per-horizon inference-time filtering.

**Parameterizable.** The set of horizons is configurable per agent or per evaluator run, not hardcoded. Standard set: `{1m, 3m, 6m, 1y}`. Toys may use shorter horizons (days or flips) for fast iteration. New horizons can be added without architectural change.

**Connection to memory architecture.** Per [memory-design.md](memory-design.md), every L3 promoted skill carries its horizon list. Per [CONTRACT.md](CONTRACT.md), every Contract carries a horizon field. Per the Stone 9 scoreboard schema, every row carries a horizon column. The three structures align by design.

**No new structural machinery.** Multi-horizon scoring is the Stone 9 scoreboard *used correctly* — slicing by an existing column. The conceptual move is bigger than the implementation: state is per-horizon by default; the agent's job is per-horizon forecasting; the evaluator's job is per-horizon scoring.

**One sentence.** The same belief means different things at different horizons; the agent emits one Contract per horizon; the scoreboard scores each independently; the system discovers where each agent's edge lives empirically — and the per-horizon promotion gate ensures skills only act where they're validated.

### Stone 11 — expression-type tagging within `TradeAction`

**The setup.** When the agent decides to trade, it must also choose **how** to express its belief. The same belief ("AAPL is strengthening") can be expressed many different ways — each with a different payoff profile under each outcome.

**The expression-type categories** (what the `expression_type` column on the scoreboard records):

| `expression_type` | Payoff shape |
|---|---|
| `equity-long` / `equity-short` | Linear in price move; symmetric upside/downside |
| `option-call` / `option-put` | Asymmetric; capped downside (premium paid), big upside above/below strike |
| `option-spread` | Asymmetric with both upside and downside capped; cheaper than naked option |
| `option-straddle` / `option-strangle` | Profits from large moves in either direction |
| `vol-long` / `vol-short` | Profits from realized vs implied volatility difference, regardless of direction |
| `pair` / `relative-value` | Profits from one underlying outperforming another; hedged against market direction |

**Critical distinction — category vs full spec.** `expression_type` on the scoreboard is the **broad category**. The specific trade details — underlying, strike, expiration, premium, direction (long or short the contract), size — live **inside the `TradeAction` object** on the Contract. Example:

```
TradeAction {
  expression_type: "option-call"          ← scoreboard column captures THIS
  underlying:      "AAPL"
  direction:       "long"
  strike:          210
  expiration:      "2026-08-15"
  size:            10  contracts
  premium_paid:    $250  per contract
}
```

The scoreboard slices on the category because that's where statistical power lives. The full spec lives on the Contract for payoff math (Stones 13 and 14).

**Why category-level slicing.** With ~hundreds of trades over a year, you have many trades per category but few per specific strike-expiration combo. Slicing at the category level gives you statistical reads like *"this agent's mean Brier on option-call trades is 0.21; on equity-long trades is 0.18"* — meaningful comparisons. Slicing at the strike-by-strike level would give one row per unique trade, no aggregation possible.

**Per-expression-type promotion gate.** Same shape as Stone 10's per-horizon gate. A candidate skill is tested per expression type:

| Check at expression type | equity-long | option-call | vol-spread | pair |
|---|:---:|:---:|:---:|:---:|
| Held-out calibration improves | ✓ | ✓ | ✗ | ✓ |
| Cross-model regression | ✓ | ✓ | (n/a) | ✓ |
| Survivorship check | ✓ | ✓ | (n/a) | ✓ |

→ Promoted with `expression_type: [equity_long, option_call, pair]`. Excluded from `vol-spread` context by the domain-of-validity filter. **A skill that doesn't validate at a given expression doesn't get to act there.** Prevents the "skill that worked on equity-direction leaks into options-trading" failure mode.

**`NoAction` is a typed peer of `TradeAction`, not an expression type.**

```
Agent's action layer:
  ├── TradeAction
  │     ├── equity-long / equity-short
  │     ├── option-call / option-put / option-spread / option-straddle
  │     ├── vol-long / vol-short
  │     └── pair / relative-value
  └── NoAction  (← peer, not a sub-type; scored by Stone 13)
```

`NoAction` is scored on whether the agent correctly recognized the absence of edge — a different scoring path from any `TradeAction` (which is scored against a payoff structure). BIAS_PATTERNS #12 (trade-for-trade's-sake) is the defense `NoAction` provides.

**Stacking with Stone 10.** A skill's domain-of-validity can carry BOTH `horizon: [list]` AND `expression_type: [list]` AND `sector: [list]`. Three independent slicing dimensions. A skill might be valid only at `horizon: [3m, 6m]` AND `expression_type: [equity_long]` AND `sector: [tech_hardware]` — narrowly tagged, narrowly applied. Prevents leakage across dimensions.

**Connection forward.** Stone 13 (decision-quality) will use the *full* `TradeAction` details (strike, expiration, premium, etc.) to score whether the chosen specific trade matched the belief and the cost structure. Stone 14 (capacity-adjusted return) will use the same details to compute realistic P&L at deployable size.

**In code.** `expression_type` is a string field on the scoreboard row (Stone 9 schema); `TradeAction` is the typed sum from [CONTRACT.md](CONTRACT.md). The full `TradeAction` object is stored alongside the scoreboard row for downstream payoff computation.

**One sentence.** `TradeAction` has sub-types (equity-long, option-call, vol-spread, pair, …); `expression_type` on the scoreboard is the broad category for slicing; specific trade details live inside the `TradeAction` object; per-expression-type promotion gate ensures skills only act in expression contexts where they've been validated; `NoAction` is a typed peer of `TradeAction`, handled by Stone 13.

### Stone 11b — the Forecast Ledger (Constitution v5)

**The setup.** When an agent says "I'm 95% sure the realized log return falls in `below_minus_5`," you cannot trust the 95% on its face. The agent might be a confident liar, a careful Bayesian, or a coin-flipper dressed up in confident language. **The 95% means whatever the agent's historical track record at that confidence level means.** The Forecast Ledger is the book that lets you check.

**What the Ledger records.** One row per Contract:

| Column | What it is |
|---|---|
| `signal_class_id` | The agent's own tag for this kind of forecast (e.g., `bayesian_3state_toy`, `mid_cap_tech_margin_surprise_q3`). The agent invents and evolves these tags. Searchable, not a fixed ontology. |
| `forecast` | The agent's full distribution over the realized-return buckets — five probabilities that sum to 1. |
| `realized_bucket` | The actually-realized bucket at horizon. |

Append-only. Forecasts are snapshotted defensively so caller mutation can never poison history. The Phase 1 NEW MVP is in-memory; the Phase 2 NEW real-data version is a Postgres view over `forecasts` + `realized_returns`. **Same read API in both** — the swap is a backing-store change, not an interface change.

**The read API — `reliability_for_signal_class(signal_class_id)`.** For all rows tagged with this signal class, expand each row into N_BUCKETS `(claim, outcome)` pairs (one per return bucket: claim is the agent's stated probability for that bucket, outcome is 1 iff that bucket realized). Pool those pairs across all rows; bin the claims into equal-width bins on [0, 1]; report per-bin (mean claim, observed rate, count).

This is the standard reliability-bucketing pattern from Stone 8, but **per signal class**.

**Three worked tables from the toy** (100 episodes, 5 return buckets, seed=42, generated by `uv run python -m fingym.toys.ledger_demo`):

**`confident_static`** — ConfidentAgent (always 95% on `below_minus_5`, ignores all evidence):

| claim range | avg claim | observed | count | gap |
|---|---:|---:|---:|---:|
| [0.00, 0.10) | 0.013 | 0.182 | 400 | -0.170 |
| [0.90, 1.00) | 0.950 | 0.270 | 100 | +0.680 |

Reads: *95% claim → 27% truth. Bullshitter caught.*

**`uniform_static`** — UniformAgent (always 0.2 per bucket, never updates):

| claim range | avg claim | observed | count | gap |
|---|---:|---:|---:|---:|
| [0.20, 0.30) | 0.200 | 0.200 | 500 | 0.000 |

Reads: *perfectly on the diagonal — but only one row. No varying confidence levels = no discriminating information.*

**`bayesian_3state_toy`** — BayesianAgent (updates on each emission):

| claim range | avg claim | observed | count | gap |
|---|---:|---:|---:|---:|
| [0.00, 0.10) | 0.014 | 0.078 | 295 | -0.064 |
| [0.40, 0.50) | 0.445 | 0.404 | 57 | +0.042 |
| [0.50, 0.60) | 0.563 | 0.276 | 29 | +0.287 |
| [0.90, 1.00) | 0.953 | 0.619 | 21 | +0.334 |

Reads: *broad calibration in the bulk; mild overconfidence at the extreme (the conditional-independence flaw — the agent treats correlated emissions as independent evidence). Cluster B's shrinkage corrects this without retraining the agent.*

**Why per-signal-class, not global.** A single agent might be calibrated on `mid_cap_tech_margin_surprise_q3` and miscalibrated on `mega_cap_macro_rate_shock`. Pooling all forecasts globally would average away the structure. Per-signal-class slicing surfaces the structure for action-time calibration. **The agent owns the tag; the verifier owns the bookkeeping; reliability is an empirical property of the `(agent, signal_class)` pair.**

**What the Ledger is NOT.** It does not act. It does not size. It does not shrink the forecast. It records and returns. **Cluster B** (Stones 11c + 11d) is what reads the Ledger at action time and decides what to do with the empirical track record.

**Connection forward.** Stone 11c (calibration shrinkage) reads `reliability_for_signal_class` to shrink a fresh forecast toward the agent's empirical truth-rate before the action gate sees it. Stone 11d (Tradable-Edge Action Engine) gates trade/NoAction on calibrated expected utility, not raw forecast confidence. An agent that systematically claims 95% but is right 25% of the time will see its fresh forecast shrunk to ~25%, fail the action gate, and emit `NoAction`. That is how the Ledger turns the agent's confidence *words* into checkable, money-relevant *numbers*.

**Adversarial verification.** `tests/integration/test_forecast_ledger_cluster_a.py` feeds Confident, Uniform, and Bayesian through the toy + Ledger and asserts each signal class produces a distinguishable reliability signature: ConfidentAgent's high-claim bucket has gap > 0.4 (overconfidence) and low-claim bucket has gap < -0.1 (underconfidence); UniformAgent's single bucket sits within 1e-9 of the diagonal; BayesianAgent's well-sampled buckets (count ≥ 50) sit within 0.15 of the diagonal. Any future change that breaks the discrimination fires the gate.

**In code.** `src/fingym/ledger/forecast_ledger.py` (`ForecastLedger.record`, `.reliability_for_signal_class`, plus audit accessors); `src/fingym/toys/ledger_demo.py` (printed inspection surface — the three tables above are emitted by `uv run python -m fingym.toys.ledger_demo`). Module init at `src/fingym/ledger/__init__.py` documents the import boundary: `agents/`, `action/`, `evaluator/`, `cli/` may read the Ledger; the Ledger must not import from `agents/` or `action/`. The real-data migration in Phase 2 NEW swaps the in-memory backing store for a Postgres view; the read API is unchanged.

**One sentence.** The Forecast Ledger is the append-only book that records every `(forecast, realized bucket)` pair indexed by the agent's self-applied `signal_class_id`; its read API answers "for this signal class, when the agent claimed X% confidence on a bucket, what fraction realized?" — the empirical truth-rate that Cluster B's shrinkage will apply to the agent's raw forecast before the action gate sees it.

### Stone 11c — calibration shrinkage (Constitution v5)

**The question.** The Ledger says: "ConfidentAgent has historically been right ~27% of the time when claiming 95% in this signal class." Today the agent claims 95% again. Should the action gate see **0.95** (the agent's claim) or **0.27** (the Ledger's empirical)? **Neither alone** — take a weighted blend. The weight depends on how much Ledger history you have.

**The intuition.** No history → trust the agent (nothing else to go on). Lots of history → trust the empirical record. In between → blend. **The Ledger sample size is the dial.**

**Worked example — ConfidentAgent's 0.95 raw claim, empirical = 0.27, `prior_strength = 20`:**

| Ledger sample size `n` | raw | empirical | weight on empirical | **shrunk** |
|---|---:|---:|---:|---:|
| 0 (new signal class) | 0.95 | — | 0.00 | **0.95** |
| 5 | 0.95 | 0.27 | 0.20 | **0.81** |
| 20 | 0.95 | 0.27 | 0.50 | **0.61** |
| 50 | 0.95 | 0.27 | 0.71 | **0.46** |
| 100 | 0.95 | 0.27 | 0.83 | **0.38** |
| 1000 | 0.95 | 0.27 | 0.98 | **0.28** |

Reads: with no Ledger, the gate sees 0.95. With 100 forecasts of history, the gate sees 0.38. With 1000, the gate sees 0.28 — the empirical truth-rate has effectively replaced the agent's claim. The agent never knows the gate saw a different number.

**Applied to the three Cluster A signal classes (after 100 Ledger episodes):**

| Signal class | Raw 0.95 claim becomes... | Why |
|---|---:|---|
| `confident_static` | ~0.38 | Empirical 0.27 with `n=100` in [0.9, 1.0); raw crushed toward truth |
| `uniform_static` | (never claims 0.95) | Raw is always 0.20; nothing to crush |
| `bayesian_3state_toy` | ~0.78 | Empirical 0.62 with `n=21` in [0.9, 1.0); raw shrunk modestly |

The careful thinker's 0.95 gets nudged a little (mild overconfidence; small sample in this bin). The liar's 0.95 gets crushed to a third of its size. **No retraining of the agent required** — the verifier does this in flight.

**Three properties to lock in:**

1. **Empty Ledger = identity.** New signal class → no entries → shrinkage returns the raw forecast unchanged. The system always works on day 1. (Cost: a brand-new signal class with overconfident claims slips through until the Ledger fills. The Stone 11d margin-of-safety threshold absorbs this — shrinkage alone does not.)
2. **Sparse Ledger = gentle.** Small `n` → low weight on empirical → mild shrinkage. Reflects appropriate uncertainty about a small-sample empirical estimate.
3. **Dense Ledger = aggressive.** Large `n` → high weight on empirical → the verifier essentially overwrites the agent's claim with the empirical truth-rate.

**Formula (shorthand for the table above):**

```
shrunk = (n × empirical + k × raw) / (n + k)
weight_on_empirical = n / (n + k)
```

`n` = Ledger sample size in the matching claim bin. `k` = `prior_strength` (pseudo-count weight on the raw claim; operator-tunable, default 20 in the toy MVP). `empirical` = observed truth-rate in that bin. `raw` = agent's current claim. Standard Bayesian shrinkage with pseudo-counts.

**What it operates on — bin-by-bin.** Each of the 5 return-buckets in the agent's forecast is shrunk independently using its matching Ledger claim-bin (the bin whose `[lo, hi)` contains the raw claim). After all 5 are shrunk, renormalize the distribution to sum to 1.

**Why per-bin and not full-distribution.** The Ledger's reliability data is per-claim-bucket, not per-full-forecast. Pooling at the bin level gives statistical power — 100 episodes × 5 buckets = 500 (claim, outcome) pairs per signal class. Full-distribution shrinkage would require orders of magnitude more samples to estimate the agent's joint miscalibration over all 5 buckets simultaneously.

**The `prior_strength` knob.** Architectural choice: shrink toward Ledger empirical. Operator choice: how aggressively. `k = 20` means "treat the agent's raw claim as worth 20 pseudo-observations of history" — the Ledger overtakes the raw claim once it has ~20 entries. `k = 5` would be more aggressive (Ledger overtakes raw faster); `k = 100` would be more conservative (Ledger needs more history before it overtakes raw). Tunable per signal class as the system matures. **This knob belongs in the operator-tunable parameter set (DESIGN.md "Operator Configuration and Observability"), not in the architectural commitments.**

**Known weakness — regime change.** If the agent's track record changes (good in 2023, bad in 2024), the Ledger empirical *lags*. The shrunk forecast will be biased toward the obsolete regime. Mitigations exist — rolling windows, time-decay weighting, signal-class re-tagging on regime detection — but are out of scope for the Cluster B MVP. **Flagged for future stones; not solved here.** A skill that worked under one regime and fails under another will continue to clear the action gate until the Ledger catches up — that latency is real and is part of why the margin-of-safety threshold exists.

**Connection forward (Stone 11d).** `F_AI_calibrated` (the shrunk forecast) is the **only** thing the Tradable-Edge Action Engine sees. The raw forecast is preserved on the Contract for audit; it never multiplies a payoff. ConfidentAgent's 0.95 → 0.38: that 0.38 is what computes calibrated expected utility, which must clear the margin-of-safety threshold for any trade to fire.

**In code (when built — Cluster B).** `src/fingym/action/calibrator.py` will expose `shrink(raw_forecast, signal_class_id, ledger, prior_strength) -> F_AI_calibrated`. Reads `ledger.reliability_for_signal_class`; matches each raw-claim to its Ledger bin; applies the formula above; renormalizes; returns the calibrated distribution. Empty-Ledger and zero-`n` cases return the raw forecast unchanged.

**One sentence.** Calibration shrinkage rewrites the agent's raw claim toward its empirical Ledger track record via a sample-size-weighted blend — empty Ledger passes the claim through unchanged; long miscalibrated history overwrites it with the empirical truth-rate — and the resulting `F_AI_calibrated` is what (and only what) the action gate sees.

### Stone 11d — Tradable-Edge Action Engine / margin-of-safety gate (Constitution v5)

**The setup.** The calibrator (Stone 11c) hands a calibrated forecast `F_AI_calibrated` to the Action Engine. The Engine has one job: decide whether to trade, and if so how much. The decision is gated by a single signed scalar — `tradable_edge_score` — built from the calibrated forecast, a cost model, and a margin-of-safety threshold.

**The verdict.**

```
tradable_edge_score = calibrated_expected_utility − margin_of_safety_threshold
```

Positive → trade with conservative Kelly-style sizing. Non-positive → `NoAction`. **One signed scalar, one boolean.** No other path to trade exists.

**Worked example — one calibrated forecast through the pipeline.** Suppose the calibrator emits:

| Bucket | Return midpoint | Calibrated probability |
|---|---:|---:|
| `below_minus_5` | -8% | 0.10 |
| `minus_5_to_0` | -2.5% | 0.20 |
| `0_to_5` | +2.5% | 0.40 |
| `5_to_10` | +7.5% | 0.20 |
| `above_plus_10` | +12% | 0.10 |

Probability-weighted return = +2.4%. Costs (round-trip) = spread 0.30% + commission 0.10% + sqrt-law impact 0.40% + alpha decay 0.20% = 1.00%. So `calibrated_expected_utility = 2.4% − 1.0% = +1.4%`. With `margin_of_safety_threshold = 1.0%`, `tradable_edge_score = +1.4% − 1.0% = +0.4%`. Positive → trade fires.

**Three adversarial agents through the gate** (Cluster A reliability assumed, n=100 each):

| Agent (regime) | Raw → calibrated on lead bucket | Expected return after costs | `tradable_edge_score` | Verdict |
|---|---|---:|---:|---|
| ConfidentAgent (raw 0.95 on `below_minus_5`) | 0.95 → 0.38 | -1.1% on short (calibrated return ≈ -0.1%; cost eats it) | -2.1% | **NoAction** |
| UniformAgent (0.20 × 5) | unchanged | -1.0% (no direction, cost only) | -2.0% | **NoAction** |
| BayesianAgent — strong signal, well-sampled bin | mild correction | +2.2% | +1.2% | **trade** |
| BayesianAgent — strong signal, undersampled extreme | shrunk toward empirical 0.62 | +0.6% | -0.4% | **NoAction** |
| BayesianAgent — mild signal | unchanged | -0.3% | -1.3% | **NoAction** |

The bullshitter's conviction trade is killed at the gate. The uninformed agent never trades. The careful thinker trades only when both the signal AND the Ledger history support it.

**The three knobs.**

1. **`F_AI_calibrated`** is the only forecast the gate sees. Raw never multiplies a payoff. Audit only.
2. **Cost model.** In the toy MVP, a single round-trip constant (set per signal class). Cluster C extends this with per-name liquidity, square-root-law impact at deployable size, and alpha decay over horizon.
3. **`margin_of_safety_threshold`.** Operator-tunable. Conservative buffer for everything the Engine can't see: residual miscalibration, regime change since the Ledger filled, model risk, adverse selection. In the toy MVP, a module-level constant; in production, per-signal-class tuning.

**Three properties to lock in.**

1. **`NoAction` is a typed first-class peer of `TradeAction`.** Not absence-of-decision; an emitted decision. Scored on the same coherence shape by Stone 13 — good restraint is graded the same way good trades are. Defends against BIAS_PATTERNS #12 (trade-for-trade's-sake).
2. **The threshold is the only thing between a calibrated edge and a trade.** A 0.1% edge over 0% threshold trades. A 0.9% edge over 1.0% threshold doesn't. Operator tunes threshold for risk appetite; the cost model is determined by reality, not preference.
3. **Sizing is fractional Kelly, not full Kelly.** Full Kelly maximizes long-run log-wealth but is volatility-pessimal under estimation error. The toy MVP uses `k = 0.25` (quarter Kelly); production tunes per signal class.

**Connection forward.** Stone 11e (Market-State Baseline) runs an identical Action Engine on a code-level-isolated baseline forecast; the audit layer computes `incremental_AI_edge = AI realized edge − Baseline realized edge` as an attribution column. Stones 13 (decision coherence) and 14 (capacity-adjusted realized return) consume `tradable_edge_score` and the chosen `TradeAction` for scoring.

**In code (when built — Cluster B 11d-b).** `src/fingym/action/action_engine.py` will expose `decide(calibrated_forecast, cost_model, threshold) -> TradeAction | NoAction`. The function computes `calibrated_expected_utility` under the calibrated distribution, subtracts costs, compares to the threshold, and emits either a `TradeAction` with fractional-Kelly sizing or `NoAction`. Both populate the Contract's `final_action`, `calibrated_expected_utility`, and `tradable_edge_score` fields.

**One sentence.** The Tradable-Edge Action Engine emits one signed scalar — `tradable_edge_score = calibrated_expected_utility − margin_of_safety_threshold` — as the single gate between forecast and trade; `NoAction` is a typed first-class peer, positive verdicts trade at fractional Kelly under `F_AI_calibrated`, the raw forecast never multiplies a payoff, and operator preference enters only through the threshold and Kelly fraction.

### Stone 11e — Market-State Baseline (Track C) isolation (pending teaching)

Under Constitution v5, a separate `src/fingym/baseline/` module reads only headline observables (rates, vol, FX, commodities) and emits its own forecast distribution. Code-level isolation: `agents/` cannot import from `baseline/` (import-linter rule). The Baseline's processed forecast is never seen by the AI Core; the audit layer computes `incremental_AI_edge = AI realized edge − Baseline realized edge` as an attribution column. The Baseline runs an identical Action Engine on its own forecast.

The full distilled summary with worked tables — what the headline-observables space looks like, the Baseline's forecasting model (kept deliberately simple), the attribution math — lands when Stone 11e is taught (Cluster I).

### Stone 12 — process-quality flag (narrow form) — v5 reframing pending teaching

**Survives Constitution v5 at the concept level.** The mechanical check is unchanged: was there an emission with `as_known` in the window before this forecast update? If yes, `motivated`; if no, `unmotivated`. Per-agent `unmotivated_update_rate`, hard-capped at promotion (initial value: 0.10).

**What changes under v5.** The pre-v5 distilled summary referenced Stone 11a's `belief_delta_on_truth` as the complementary defense against the sophisticated price-tracker (the agent that waits for an emission then mirrors the market). Under v5 the complementary defense is the Forecast Ledger's per-signal-class reliability (Stone 11b) and the Tradable-Edge Action Engine's calibrated expected utility gate (Stone 11d) — an agent that systematically mirrors the market will accumulate low reliability per signal class and produce a near-zero `tradable_edge_score`, getting filtered at the action gate.

**Two parked architectural questions** still apply (see [DECISIONS.md](DECISIONS.md) "Open architectural questions"): emission-triggered vs agent-driven architecture; emissions taxonomy. Both reopen at Phase 2 NEW Stone 22-23.

The v5-reframed full distilled summary with worked tables lands when Stone 12 is re-walked in the upcoming v5 teaching pass.

### Stone 13 — decision-quality with NoAction as first-class peer — v5 reframing pending teaching

**Survives Constitution v5 at the concept level.** Per-Contract coherence checks on the agent's action against the inputs (forecast, calibrated expected utility, margin-of-safety threshold, costs, expression-type fit). `NoAction` as a typed peer of `TradeAction`, scored on the same shape so "good restraint" is graded the same way "good trades" are (defends against BIAS_PATTERNS #12 trade-for-trade's-sake).

**What changes under v5.** Pre-v5 threshold-match used `gap on the truth-candidate state > cost` (where `gap = belief_delta(S) = P_AI(S) − P_market(S)`). Under v5, threshold-match uses `tradable_edge_score > 0` (the Tradable-Edge Action Engine's gate verdict, where `tradable_edge_score = calibrated_expected_utility − margin_of_safety_threshold`). The verifier-side coherence question becomes: did the agent's `recommended_action` agree with the engine's gate verdict? Direction-match and expression-match keep their pre-v5 spirit (right side of the directional signal; expression fits forecast shape) but operate on the v5 calibrated forecast.

`decision_quality_rate` remains a scoreboard column (not a hard cap). The v5-reframed full distilled summary with worked tables and concrete numbers lands when Stone 13 is re-walked in the upcoming v5 teaching pass.

### Stone 14 — capacity-adjusted realized return (Constitution v5)

**The setup.** Stone 11d gates trades on *expected* edge after a single flat round-trip cost (the Cluster B placeholder). The scoreboard needs the *backward-looking* counterpart: per-Contract realized P&L after all frictions actually paid, sliced by deployable size bucket. That's the `realized_edge` column. The flat cost in Cluster B gets replaced here with the structured decomposition.

**The decomposition.**

```
realized_edge = nominal_payoff − spread − commission − market_impact(size, ADV) − alpha_decay
nominal_payoff = realized_return × direction × notional
```

`realized_return` comes from the labelling function at horizon (Stone 2; v5 `RealizedReturnPlan` on the Contract). `direction` is +1 for long, −1 for short. The four friction components live in the structured cost model — same components Stone 11d's Action Engine consumes forward-looking; here they're consumed backward-looking on the actual trade.

| Component | What it captures | Toy MVP | Real-world range |
|---|---|---:|---|
| spread | bid-ask cost; half on entry + half on exit | 5 bps | 1–50 bps |
| commission | explicit broker fees | 1 bp | 0.5–2 bps |
| market_impact | sqrt-law price impact at deployable size | 50 bps × √(size/ADV) | varies |
| alpha_decay | edge fades over horizon as the thesis publishes itself | 5 bps/month | 0–50 bps |

**Square-root law — the only non-obvious piece.** Market impact follows `k × sqrt(size / ADV)`, not linear. Why sqrt: book depth empirically follows a sqrt shape under standard microstructure (Kyle 1985; Almgren-Chriss). Small trades sit at the inside spread; large trades walk up the book. Worked numbers with `k = 0.005` (50 bps per √ADV):

| Fraction of ADV | sqrt | Impact (bps) |
|---:|---:|---:|
| 0.1% | 0.032 | 1.6 |
| 1% | 0.10 | 5.0 |
| 5% | 0.22 | 11.2 |
| 10% | 0.32 | 15.8 |
| 25% | 0.50 | 25.0 |
| 100% | 1.00 | 50.0 |

**Size buckets — why this is a column, not a hard cap.** Same +3% nominal forecast, same direction, different deployment size against TOY (ADV $10M):

| Deployment size | Frac of ADV | Total costs | Realized edge |
|---|---:|---:|---:|
| $10k (small) | 0.1% | ~13 bp | **+2.87%** |
| $100k (medium) | 1% | ~16 bp | **+2.84%** |
| $1M (large) | 10% | ~27 bp | **+2.73%** |
| $10M (massive) | 100% | ~61 bp | **+2.39%** |

A microcap underlying (ADV $500k) at the same $100k notional is 20% of ADV — impact ~22 bps, total ~34 bps. Same forecast, very different realized P&L. **The scoreboard reports realized_edge per Contract; aggregations slice by size bucket, signal class, agent. The slice reveals where the agent is profitable and where they shouldn't deploy.**

**NoAction Contracts: `realized_edge = 0` cleanly.** No trade, no costs, no P&L. NoActions still get a scoreboard row with realized_edge populated as 0 — they participate in agent-level aggregations (mean realized_edge per agent treats NoActions as zero-payoff peers of trades; defends BIAS_PATTERNS #12 trade-for-trade's-sake at the scoring layer).

**Three properties to lock in.**

1. **realized_edge is backward-looking; calibrated_expected_utility is forward-looking.** Stone 11d's expected utility is what the agent expected at decision time. Stone 14's realized_edge is what the world actually delivered. The pair forms a calibration audit: an agent with high expected utility but consistently low realized_edge is forecasting badly, not just unlucky.
2. **The near-tautological structural check: mean realized_edge at the agent's stated deployable size, across many trades, must be > 0.** A negative mean is a friction-eater, not a profitable agent. Column-level threshold, not a hard cap on individual trades — single-trade noise must not gate skill.
3. **The square-root impact law is the load-bearing piece of the cost structure.** Without it, a strategy looks linearly scalable to any size, and the scoreboard cannot surface capacity ceilings. The sqrt is what makes the deployable-size-bucket slice meaningful — a Kelly-optimal trade at $10k can be a losing trade at $10M.

**Connection forward.** Stone 11d's Action Engine consumes the same structured cost model forward-looking: `calibrated_expected_utility = |E[r_calibrated]| × notional − round_trip_cost_at(notional, horizon_periods)`. The Cluster B flat `round_trip_cost` field gets replaced by a method on the structured model. Stone 11e (Market-State Baseline) compares the AI Core's realized_edge to the Baseline's realized_edge to produce the `incremental_AI_edge` column.

**In code (Cluster C 14-b).** `src/fingym/action/action_engine.py` replaces `ToyCostModel`'s single `round_trip_cost` field with structured fields (`adv`, `spread_bps`, `commission_bps`, `impact_coefficient`, `alpha_decay_bps_per_period`) plus a `round_trip_cost_at(notional, horizon_periods)` method. `src/fingym/evaluator/realized_edge.py` exposes `realized_edge(action, realized_return, cost_model, horizon_periods) -> float` for scoreboard population; returns 0 for NoAction.

**One sentence.** Stone 14's `realized_edge` column is the backward-looking per-Contract P&L — `nominal_payoff` (= realized_return × direction × notional) minus structured frictions (spread, commission, sqrt-law market impact at deployable size, alpha decay) — sliced primarily by size bucket; mean realized_edge at the agent's stated size must be positive in aggregate, with NoAction carrying `realized_edge = 0` as a typed first-class peer of trades.

---

**Layer 2 — the evaluator's math — substantially complete through Phase 0.** Stones 8 (calibration), 9 (scoreboard), 10 (multi-horizon), 11 (expression-type tagging) all taught and distilled under pre-v5 framing; their distilled summaries survive Constitution v5 with the language updates above (forecast over realized returns; signal_class_id added to the scoreboard schema; per-signal-class reliability added as a Forecast Ledger slicing dimension). Stones 11a (market-delta scoring) and 31 (market-implied belief recovery) were removed by Constitution v5. New v5 stones 11b (Forecast Ledger), 11c (calibration shrinkage), 11d (Tradable-Edge Action Engine / margin-of-safety gate), and 11e (Market-State Baseline isolation) are introduced and land via the upcoming v5 teaching pass. Stones 12, 13, 14 survive at the concept level; their distilled summaries are v5-reframed above with full re-teaching pending. Next in the build: the **v5 teaching pass starting from Stone 1 forward** (quick confirm for unchanged stones; full teach for 7b / 11b / 11c / 11d / 11e and v5 reframings for 12 / 13 / 14 / 15).

---

## Layer 3 — Evaluator validated on toys

### Stone 15 — the synthetic-market toy — v5 refactor pending teaching

**Phase 0 closed this stone under pre-v5 framing.** The toy was built as a 3-state two-believer setup (agent + market with different priors) with a `belief_delta_on_truth` scoring path. It lived at [src/fingym/toys/synthetic_market.py](src/fingym/toys/synthetic_market.py) and reproduced PYRAMID Stone 11a's worked example by code (Brier/log_score identical across same-`P_AI` scenarios; `belief_delta_on_truth` distinguishes edge / no-edge / anti-edge).

**The Constitution v5 cleanup pass (2026-05-18) removed:**
- The two-believer parallel run (`run_two_believers`)
- The scoreboard demo that reproduced Stone 11a (`run_scoreboard_demo`)
- The `STONE_11A_AGENT_PRIOR` and `STONE_11A_MARKET_PRIOR` constants
- The `belief_delta_on_truth` function in `src/fingym/evaluator/scoring.py`

**What survives:** the single-believer skeleton (`run` function; `World`, `BayesianBeliever`); the likelihood-table physics; `brier`, `log_score`, `reliability_buckets`.

**The v5 refactor — Phase 1 NEW Cluster A deliverable.** The toy emits realized returns at horizon. A single Bayesian believer forecasts the next realized return's distribution, tagged with a signal class. The Forecast Ledger MVP records each (forecast, realized return) pair and computes per-signal-class reliability empirically. The v5 distilled summary with worked tables and concrete numbers lands when Cluster A is taught.

---

## Layer 4 — Real-data discipline (toy-first mechanisms; Phase 1 NEW Cluster E)

> The data-spine stones (22, 23, 25, 27, 28) instantiate against real data in Phase 2 NEW. Stones 24 (PIT discipline) and 26 (survivorship + delistings) are first exercised as toy mechanisms here in Phase 1 NEW Cluster E. Phase 2 NEW substitutes real vendor `as_known` timestamps and real corporate-action feeds into the same plumbing — the guard, the store, and the agent contract don't change.

### Stone 24 — point-in-time discipline (toy mechanism, Constitution v5)

**The setup.** Real markets revise data. The Q1 2026 revenue reported as $100M on 2026-04-15 can become $97M on 2026-07-30 after an audit. An agent forecasting on 2026-05-01 must see only $100M, never $97M. Without point-in-time discipline at the architecture level, vendor revisions silently leak future information into past predictions — and the failure is invisible because the data file says "Q1 revenue $97M" with no timestamp telling you when that number became known.

**Two timestamps per record.** Every emission, derived_evidence, and headline_observable carries:

| Timestamp | What it captures |
|---|---|
| `as_of` | the time the data REFERS TO (e.g., the tick of the period being reported) |
| `as_known` | the time the data became KNOWN to the world (publish tick) |

**The PIT rule.** An agent at decision-time `t` may only see records with `as_known ≤ t`. The `as_of` is unrestricted — an agent at 2027 can reason about Q1 2026 by reading records with `as_of = Q1-2026, as_known ≤ now`.

**Restatements as separate records.** A revision is a NEW record with the same `as_of` but a later `as_known` and a different value. The store keeps the full revision history append-only — closest to how real vendors actually deliver (XBRL revisions, EDGAR amendments). The `time_leak_guard(records, query_tick)` function queries: return all records with `as_known ≤ query_tick`, and for each `as_of` group, pick the latest one.

**Worked restatement table.** A toy emission `(as_of=3, value=strong, as_known=10)` arrives at tick 10. At tick 25, a revision `(as_of=3, value=weak, as_known=25)` is published. The PIT view at four query times:

| Query tick | Records with `as_known ≤ query` | Latest per `as_of=3` |
|---:|---|---|
| 5 | (none with as_of=3) | (data not yet published) |
| 15 | (initial only) | `strong` |
| 22 | (initial only) | `strong` (revision not yet out) |
| 30 | (initial + revision) | `weak` (latest known) |

**The non-obvious part.** An agent's forecast at tick 15 must NOT be allowed to peek at the tick-25 revision just because we (the test writers) know it's coming. The guard makes this structurally impossible: it only returns records whose `as_known ≤ query_tick`.

**Three properties to lock in.**

1. **Append-only audit trail.** Restatements never mutate prior records. The store keeps every version with its `as_known`; aggregations are PIT queries against the immutable history.
2. **Time-leak guard is a single function, not scattered checks.** The guard IS the mechanism. No agent code asks "is this date safe?"; the verifier feeds the agent only what was PIT-visible at the agent's decision time.
3. **PIT discipline is the same code path for synthetic and real data.** Cluster E exercises this in toy mode; Phase 2 NEW substitutes real records carrying real `as_known` timestamps from vendors. The guard, the store, and the agent contract don't change.

**Connection forward.** Stones 12 and 13 (process quality + decision quality) rely on `as_known` to define "the emission window for this update" — what emissions were known just before this forecast was emitted. Stone 27 (trajectory store as year-2 SFT fuel) is PIT-disciplined by construction so the SFT-fit format is correct for any replay date.

**In code (Cluster E 24-b).** `src/fingym/toys/synthetic_market.py` gets an `Emission` frozen dataclass with `as_of: int`, `as_known: int`, `value: EmissionValue` fields. A `time_leak_guard(emissions, query_tick) -> list[Emission]` function returns the PIT view — filter by `as_known`, dedupe per `as_of` keeping latest. Restatements are added by appending another `Emission` record with the same `as_of` and a later `as_known`. The existing `sample_emission(state, rng)` continues to return raw `EmissionValue` strings for backward compat; new helpers build typed `Emission` records.

**One sentence.** Point-in-time discipline enforces that an agent at decision-time `t` can only see data with `as_known ≤ t`; restatements are stored as separate append-only records with the same `as_of` and a later `as_known`; the `time_leak_guard` function is the single mechanism that returns the PIT view, and the same code path serves toy data here and real vendor data in Phase 2 NEW.

### Stone 26 — survivorship and the delisted shadow universe (toy mechanism, Constitution v5)

**The setup.** Real markets have failures: companies go bankrupt, get acquired, get taken private. A scoring system that only tracks companies *still listed today* has selected for survivors. Every aggregate — mean realized_edge, calibration ECE, even Brier — is biased upward. The agent looks better than it is because the worst outcomes are invisible.

**The delisted shadow universe.** A scoring system must include delisted companies in the training and scoring universe. Their Contracts continue to participate in agent-level aggregations even after the company stops emitting evidence. The post-delist `realized_return` is well-defined: bankruptcy = a deeply negative payoff; acquisition at a known price = a fixed positive payoff; the labelling function makes the call.

**Toy implementation.** Multi-horizon return emission is parameterized with optional `delist_at: int | None` and `delist_payoff: float | None`:

- No emissions are sampled from the company after tick `delist_at`.
- `realize_returns_at_horizons(state, rng, horizons, delist_at, delist_payoff)` returns `delist_payoff` for any horizon `≥ delist_at` and a normal draw otherwise.

**Worked example.** Agent decides at `t=0` on toy company A. Company A delists at tick 5 with `delist_payoff = -0.90` (a bankruptcy outcome). Multi-horizon scoring at `t=0` under the structured cost from Cluster C (round-trip ~30 bps):

| Horizon | Delist status | Realized return | Realized edge (long, structured cost) |
|---:|---|---:|---:|
| 3 | listed | drawn from N(state) | drawn realized return − cost |
| 6 | delisted (past `t=5`) | **-0.90** | -0.90 − cost = **-90.3%** |
| 12 | delisted | **-0.90** | **-90.3%** |

If the Scoreboard *silently dropped* the long-horizon Contracts because "company doesn't exist anymore", the agent's mean realized_edge would be inflated by the magnitude of the missing losses — silent survivorship bias. The Stone 14 column structure (NoAction has `realized_edge = 0`; trades have a signed realized_edge) handles delisted trades natively: realized_edge is just a real number, deeply negative when the trade was wrong-side of a delist.

**Three properties to lock in.**

1. **Delisted companies stay in the universe.** Their Contracts are scored at every horizon, including horizons past delist. No silent drops.
2. **`delist_payoff` is the labelling function's output for post-delist horizons.** In the toy MVP, a single fixed payoff per company. In Phase 2 NEW with real data, the labelling function reads SEC EDGAR corporate-actions for delisted CIKs (per the FMP/Massive smoke-test findings — neither vendor covers pre-2024 delisted names).
3. **Delistings stress-test the realized_edge column structure.** Stone 14's near-tautological structural check (mean realized_edge at the agent's stated size must be `> 0` across many trades) must include delisted Contracts. Otherwise a strategy that's profitable on survivors but catastrophic on delistings passes the check incorrectly.

**Connection forward.** Stone 27 (trajectory store) preserves delisted-company Contracts in the SFT-fit format — year-2 training must include the failure modes. Stone 40's promotion-gate survivorship check (the fourth of the four-check gate) is the explicit promotion-time defense; the column-level Stone 14 check is the always-on defense.

**In code (Cluster E 26-b).** The toy's `realize_returns_at_horizons` gets keyword-only `delist_at: int | None = None` and `delist_payoff: float | None = None` parameters. When `delist_at` is set, post-delist horizons return `delist_payoff` instead of a normal draw. The integration test asserts (i) post-delist horizons return exactly the configured payoff, (ii) Scoreboard rows for delisted Contracts are preserved (not dropped), (iii) realized_edge for those rows reflects the delist payoff minus structured costs.

**One sentence.** Delisted companies stay in the scoring universe with a well-defined post-delist `realized_return` (the labelling function's call: bankruptcy payoff, acquisition price, etc.); the Scoreboard never silently drops delisted Contracts; the column-level Stone 14 check is the always-on defense against survivorship bias.

---

## Layer 5 — Model-driven agent on raw evidence (toy-first instantiation; Phase 1 NEW Cluster F)

> Stone 30 is first instantiated in toy mode here in Phase 1 NEW Cluster F (LLM reads toy emissions wrapped as natural-language signals). Stones 29 (pure-code Bayesian baseline) and 33 (fractional Kelly) are largely absorbed by earlier clusters; revisit at Phase 2 NEW if real-data substitution exposes plumbing gaps.

### Stone 30 — the first model-driven agent (toy instantiation, Constitution v5)

**The setup.** The cognitive engine for the first time becomes an actual model. A frontier LLM (Claude Haiku 4.5 in the toy MVP) reads the emission stream as natural language and emits the same `(distribution, signal_class_id)` pair the hand-coded agents emitted in Clusters A–E. Downstream — calibrator (Stone 11c) → Action Engine (Stone 11d) → realized_edge (Stone 14) → Scoreboard — is unchanged. The Agent Protocol the LLM agent satisfies is the same one Confident, Uniform, and Bayesian satisfied. **Model swap is a config change, not a code change** (DESIGN.md #7).

**Three architectural commitments locked in by code structure.**

1. **`src/fingym/llm/` is the only place provider SDKs live.** The pre-commit hook `no-direct-llm-sdk-imports` enforces this structurally. Anywhere outside `src/fingym/llm/`, code depends on the typed `ForecastClient` Protocol — never on `anthropic.Anthropic`, `openai.OpenAI`, etc. directly.
2. **A typed Protocol decouples the agent from any specific provider.** `LlmAgent` consumes a `ForecastClient`; the concrete implementation (Anthropic today, OpenAI / open-weights tomorrow) is injected at construction.
3. **Tool-call structured output, not free-form text parsing.** The model is REQUIRED to call the `submit_forecast(distribution, signal_class_id, thesis_category)` tool. Output schema is type-safe; schema violations raise at the SDK boundary. Parsing failures are impossible by construction.

**What the model sees.** A generic-analyst system prompt (cached via `cache_control: ephemeral` to amortize the cost over repeated calls in a test session) plus a natural-language wrapping of the emission stream. Example user message:

```
Signal stream observed so far:
  Day 1: STRONG fundamental signal
  Day 2: MIXED fundamental signal
  Day 3: STRONG fundamental signal
  ...
```

The system prompt explains the five return buckets, the `signal_class_id` self-tagging, and forces the `submit_forecast` tool call. **It does NOT tell the model the toy's likelihood table** — that would be cheating (we are testing the verifier under a real-model cognitive layer, not the LLM doing optimal Bayesian inference). The model brings its priors; the verifier scores what comes back.

**What the model emits.**

```
submit_forecast(
  distribution = {
    "below_minus_5":     0.05,
    "minus_5_to_0":      0.10,
    "zero_to_plus_5":    0.20,
    "plus_5_to_plus_10": 0.40,
    "above_plus_10":     0.25
  },
  signal_class_id = "fundamental_uniform_bullish",
  thesis_category = "Multiple strong fundamental signals; modest tail upside."
)
```

The agent caches this response and exposes it through the `Agent` Protocol's `.forecast` property and `.signal_class_id` attribute. The Forecast Ledger keys on whatever the model wrote into `signal_class_id` — the model controls its own categorization, and the verifier tracks reliability per-tag empirically.

**Three properties to lock in.**

1. **The model writes its own `signal_class_id`.** Not the framework, not the operator. The model invents and evolves tags; the Forecast Ledger tracks empirical reliability under whatever tags emerge. Over time, tags with poor reliability get implicit penalties via Stone 11c's calibration shrinkage; tags with good reliability flow through to action time.
2. **Calibration shrinkage handles new tags gracefully.** When a freshly-instantiated LLM agent uses a `signal_class_id` the Ledger has never seen, `shrink` returns the raw forecast unchanged (the empty-ledger path). Over many runs, the Ledger fills; future forecasts under that tag get shrunk toward empirical reliability. **The LLM never knows the gate saw a different forecast** — the verifier does this in flight.
3. **The integration tests are network-dependent.** Cluster F tests make real API calls. They auto-skip when `ANTHROPIC_API_KEY` is unset (CI without secrets, devs without keys). Cost: ~$0.02 per full test run with Haiku 4.5.

**Connection forward.** Cluster G (Stones 39, 40) builds the memory + promotion gate on top of the LLM agent: the model proposes candidate memory items (`memory_update_proposal` on the Contract); promoted skills go into L3 and the LLM reads them at session start. Cluster H (Stone 38) runs ≥3 LLM-agent variants in parallel — different model x prompt x memory-subset combinations. Cluster I (Stone 11e) adds the Market-State Baseline as an attribution control.

**In code (Cluster F).**

| File | What it provides |
|---|---|
| `src/fingym/llm/contract.py` | `ForecastClient` Protocol + `ForecastResponse` frozen dataclass (distribution, signal_class_id, thesis_category) |
| `src/fingym/llm/anthropic.py` | `AnthropicClient` — wraps the `anthropic` SDK; tool-call structured output; prompt caching; reads `ANTHROPIC_API_KEY` from env |
| `src/fingym/toys/llm_agent.py` | `LlmAgent` — satisfies the `Agent` Protocol; lazy LLM call on first `.forecast` access after new observations |
| `tests/integration/test_cluster_f_pipeline.py` | 5 integration tests (smoke / full-pipeline / forecast-varies-across-streams / forecast-caching / NoAction zero-edge); auto-skip when no API key |

**One sentence.** Stone 30's LLM agent reads the emission stream as natural language, self-tags its forecast with a `signal_class_id` it chooses, and emits a structured forecast distribution via tool-call — all behind a typed `ForecastClient` Protocol so the verification machinery (calibrator → Action Engine → realized_edge → Scoreboard) treats it identically to the hand-coded adversarial agents from Clusters A–E.

---

## Layer 7 — Memory + promotion gate (toy-first mechanisms; Phase 1 NEW Clusters G + H)

> Stones 38 (population), 39 (proposer), 40 (promotion gate) are first exercised in toy mode in Phase 1 NEW Clusters G and H. Cluster G wired up Stones 39 + 40 with a single LlmAgent (checks 1 + 4 real; checks 2 + 3 stubbed). Cluster H added Stone 38 (the population) and made check 2 real — cross-model agreement is now a measured property of every L3 skill.

### Stone 38 — population variants (toy instantiation, Constitution v5)

**The setup.** Cluster F instantiated a SINGLE LlmAgent. Cluster G let a skill into L3 based on one model's data — fragile, because a Haiku-specific quirk could land in memory. The architectural defense is to run ≥3 LlmAgent variants in parallel and require any promoted skill to hold across more than one of them. The `agent_id` column already on the Scoreboard distinguishes their rows; variants share everything else.

**The Cluster H variant mix** (confirmed 2026-05-18):

| Variant | Model | Prompt style |
|---|---|---|
| `haiku_default` | claude-haiku-4-5-20251001 | default |
| `haiku_value_investor` | claude-haiku-4-5-20251001 | value-investor framing |
| `sonnet_default` | claude-sonnet-4-6 | default |

This combines **cross-prompt agreement within Haiku** (same model, different framings) with **cross-architecture agreement (Haiku vs Sonnet)**. Cost: ~$0.10 per full integration-test run (~30 API calls). Stronger cross-model signal than 3x Haiku-at-different-temperatures; cheaper than Haiku + Sonnet + Opus.

**Variants share, variants differ.**

| | Shared | Differs |
|---|---|---|
| Emission stream | ✅ same toy world | |
| Scoreboard | ✅ same scoreboard; `agent_id` distinguishes rows | |
| Calibrator + Action Engine + realized_edge | ✅ same downstream pipeline | |
| LLM model | | varies (Haiku / Sonnet) |
| System prompt style | | varies (default / value-investor) |

Future variant axes (deferred): temperature, promoted-skills subset, additional architectures (Opus).

**Three properties to lock in.**

1. **Variants are operator-controlled. Tags are model-controlled.** Variants (`LlmAgentVariant` configurations) are LlmAgent setups WE choose. Tags (`signal_class_id` strings) are categories the LLMs invent at decision time. Different concepts entirely; the cross-model check counts variant agreement on the same tag.
2. **Variants share infrastructure; differ only on cognition.** Same Scoreboard, same gate, same memory loop. The only thing different is which LLM emits the forecast and what prompt frames it. This isolates the cognition-layer variation from everything else.
3. **The promotion gate operates per-variant.** Stone 40's check 2 (cross-model regression) computes mean-Brier-under-tag INSIDE each variant's Scoreboard slice. Cross-model agreement = count of variants where that within-variant improvement passes the threshold.

**Connection forward.** Cluster I (Stone 11e) adds the Market-State Baseline as a SEPARATE entity from the population — different in kind, not in degree. The Baseline consumes only headline observables (rates, volatility, FX); the population variants all consume the full emission stream. Variants validate within-cognition robustness; the Baseline validates "is the AI doing anything beyond what a simpler model could?"

**In code (Cluster H).**

| File | What it provides |
|---|---|
| `src/fingym/memory/population.py` | `LlmAgentVariant` frozen dataclass + `DEFAULT_VARIANTS` (the 3-variant mix above) + `build_population(variants, promoted_skills)` factory that constructs one `LlmAgent` per variant |
| `src/fingym/llm/anthropic.py` | Extended `AnthropicClient` accepts a `prompt_style: str = ""` field appended to the base system prompt (so each variant can carry its own framing) |
| `src/fingym/memory/promotion.py` | `evaluate_proposal_cross_model(proposal, scoreboard, min_variants_passing)` runs check 1 within each variant's slice and counts how many pass |

**One sentence.** Stone 38's population is a set of operator-configured `LlmAgentVariant` records (model + prompt style) that run in parallel on the same emission stream and Scoreboard; cross-model regression becomes the gate's count of how many variants independently see a given tag as high-signal.

### Stone 39 — LLM as proposer of candidate memory items (toy instantiation, Constitution v5)

**The setup.** The model emits an OPTIONAL `propose_memory_item(content, signal_class_id, horizons)` tool call alongside its mandatory `submit_forecast` call. Most calls don't propose anything. The model proposes only when it identifies a generalizable insight worth promoting to the agent's long-term memory.

**What the model sees.** The system prompt instructs the model that proposing is optional and should be rare — "propose only when you genuinely see a generalizable pattern, not after every forecast." `tool_choice="any"` lets the model call either or both tools.

**What the model emits.**

```
propose_memory_item(
  content = "When 4+ of 6 fundamental signals are STRONG, expect "
            "positive realized return at horizon 1-3.",
  signal_class_id = "majority_strong_short_horizon",
  horizons = [1, 3]
)
```

The proposal is captured as a `Proposal` frozen dataclass and exposed via `LlmAgent.latest_proposal`. The promotion gate (Stone 40) decides whether to act on it.

**Three properties to lock in.**

1. **Proposing is opt-in, not mandatory.** The system prompt explicitly says "most calls should not propose anything." This keeps the cost down (fewer proposals to evaluate) and ensures the model doesn't pad memory with low-value items.
2. **The model never writes directly to memory.** Proposals enter the gate (Stone 40); the gate decides. The LLM is the *source* of memory content; the verifier is the *judge* of what gets promoted. Same separation as cognition vs verification at the forecast layer (DESIGN.md #5).
3. **The proposal is structured.** Tool-call output guarantees `content` is a string, `signal_class_id` is a string, `horizons` is a list of integers. No free-form parsing of "the model's recommendation."

**Connection forward.** Stone 40's gate evaluates proposals. Cluster H runs ≥3 LLM variants in parallel; each variant can propose; the gate's cross-model regression check (real in Cluster H) requires the calibration improvement to hold under ≥2 variants. The proposal flow doesn't change — only the gate's strictness.

**In code (Cluster G).**

| File | What it provides |
|---|---|
| `src/fingym/memory/promotion.py` | `Proposal` frozen dataclass with `content`, `signal_class_id`, `horizons`, `proposed_by_agent`. |
| `src/fingym/llm/anthropic.py` | Second tool `propose_memory_item` added alongside `submit_forecast`; `tool_choice="any"`; both tool calls parsed from the response. |
| `src/fingym/llm/contract.py` | `ForecastResponse.memory_proposal: Proposal \| None` field. |
| `src/fingym/toys/llm_agent.py` | `LlmAgent.latest_proposal` property exposes the latest call's proposal (or None). |

**One sentence.** The LLM agent emits an OPTIONAL structured `propose_memory_item` tool call alongside its mandatory `submit_forecast` call; the proposal is captured but never written directly to memory — Stone 40's gate decides whether to promote.

### Stone 40 — the four-check promotion gate (toy mechanism, Constitution v5)

**The setup.** A candidate memory item is just words until something validates it. The gate is what separates "the LLM said this" from "this is real and the agent should trust it at session start." Per DESIGN.md #4, the gate is four checks:

| # | Check | What it asks |
|---:|---|---|
| 1 | Held-out replay | Does the skill improve calibration on trajectories it was not derived from? |
| 2 | Cross-model regression | Does the improvement hold under ≥2 model engines? |
| 3 | Survivorship | Does the skill calibrate against the delisted shadow universe? |
| 4 | Domain-of-validity declared | Is the skill's scope (horizons / expression_types / sectors) explicit? |

**After Cluster H, toy mode wires up checks 1, 2, and 4.** Check 3 (survivorship) is still stubbed `passed=False`; real check 3 lands in Phase 2 NEW (real delisted universe). The audit trail is *honest* about what was and was not validated.

**Check 1 (toy interpretation): does the proposed signal_class_id show better calibration than the agent's overall average?** Concretely: gather the Scoreboard rows tagged with the proposal's `signal_class_id`; require at least `MIN_HELD_OUT_ROWS = 10` of them; compute the tag's mean Brier; require it to beat the overall mean Brier by at least `MIN_CALIBRATION_DELTA = 0.01`. **Under Cluster H, check 1 runs PER VARIANT** — once inside each variant's slice of the Scoreboard. Real held-out replay (re-running the LLM with the skill in the prompt) lands in Phase 2 NEW.

**Check 2 (toy interpretation; new in Cluster H): does the calibration improvement hold under ≥`MIN_VARIANTS_PASSING` variants?** Default `MIN_VARIANTS_PASSING = 2`. Concretely: run check 1 inside each variant's slice; count the variants where check 1 passes. If the count is ≥ MIN_VARIANTS_PASSING, check 2 passes. The `models_validated` list on the resulting `CrossModelRegressionResult` carries the agent_ids of the variants that confirmed.

**Check 4 (toy interpretation): literal.** The proposal's `signal_class_id` must be a non-empty string and `horizons` must be a non-empty list. Without both, the gate has no idea where the skill applies.

**Worked example (Cluster H).** Three variants in the population: A=`haiku_default`, B=`haiku_value_investor`, C=`sonnet_default`. A proposal for `signal_class_id="growing_revenues"`. Each variant's Scoreboard slice is evaluated independently:

| Variant | rows tagged `growing_revenues` | variant's mean Brier under tag | variant's overall mean Brier | check 1 result |
|---|---:|---:|---:|---|
| A (`haiku_default`) | 12 | 0.18 | 0.32 | ✅ +0.14 delta |
| B (`haiku_value_investor`) | 14 | 0.30 | 0.30 | ❌ 0 delta |
| C (`sonnet_default`) | 15 | 0.20 | 0.34 | ✅ +0.14 delta |

Check 2 verdict: 2 of 3 variants confirm → ✅ passed. `models_validated = ["haiku_default", "sonnet_default"]`. Check 4 passes (non-empty sci + horizons). Check 3 still stubbed `passed=False, delisted_sample_size=0`. **Promotion decision: checks 1 + 2 + 4 → promoted to L3.**

If only one variant had confirmed, check 2 would fail and the proposal would land in L2 (probationary) rather than L3. Re-validation cycles could later lift it to L3 if subsequent rows tip a second variant into agreement, or retire it if it never gathers cross-model support.

**L2 tier becomes real (new in Cluster H).** Cluster G collapsed L1+L2 — the gate either promoted to L3 or rejected. Cluster H makes L2 real:

| Outcome of the gate on a proposal | Tier |
|---|---|
| Check 4 fails OR no variant's check 1 passes | rejected (None) |
| Checks 1 + 4 pass for ≥ 1 variant, but check 2 doesn't yet meet MIN_VARIANTS_PASSING | **L2** — `memory_registry/probationary/<id>.yaml` |
| Checks 1 + 2 + 4 all pass | **L3** — `memory_registry/promoted/<id>.yaml` |

L2 artifacts have the same `MemoryArtifact` schema as L3 (with `tier="L2"`); `promotion_check_results.cross_model_regression.passed=False`. They sit in the probationary directory until re-validation promotes or retires them.

**Re-validation cycles (new in Cluster H).** Memory isn't write-once. As the Scoreboard fills, the gate is re-run periodically on every existing artifact:

| Outcome | What happens |
|---|---|
| L3 artifact: still passes checks 1+2+4 | Stays L3 |
| L3 artifact: now fails one or more live checks | Demoted to L2 (`tier` updated; audit_trail records the demotion) |
| L2 artifact: now passes checks 1+2+4 | Promoted to L3 |
| L2 artifact: has been in L2 for N+ re-validation cycles without passing | Retired (`status="retired"`; file stays in git for audit) |

Trigger: **every `REVALIDATION_INTERVAL_ROWS = 50` new Scoreboard rows** (operator-tunable module constant). The function `revalidate(scoreboard, l3_dir, l2_dir)` runs deterministically when called; the toy test exercises it manually after every test episode batch.

**The architectural payoff of honest stubs.** When Cluster H's commit lands and check 2 goes real, every Cluster G L3 artifact gets re-evaluated. Skills that only worked for one variant (or whose proposing-variant's data no longer confirms) correctly demote to L2 — they were never properly cross-model-validated, and the audit trail showed that all along. The demotion isn't a failure; it's the system working as designed (see [DECISIONS.md "Honest stubs in the toy-mode promotion gate"](DECISIONS.md)).

**Three properties to lock in.**

1. **The gate is honest about what it validated.** Check 3 remains stubbed `passed=False` in toy mode, NOT `passed=True` with placeholder values. When Phase 2 NEW wires up real check 3, every current toy-mode L3 will be re-evaluated against it; survivors stay, the rest demote.
2. **The gate decides, not the model.** The LLM proposes; the gate evaluates. Cross-model regression is a structural constraint on what the LLM can self-promote — it can't just declare a skill valid; ≥2 independent cognition setups have to confirm.
3. **Promoted artifacts are append-only on disk.** YAML files in two directories (`promoted/` and `probationary/`). Demotion / promotion / retirement is a status change in a new commit, not a deletion. Full audit history is preserved.

**Connection forward.** Phase 2 NEW adds the real delisted universe (Stone 26 in real-data mode) so real check 3 lands. Real held-out replay (re-running the LLM with the skill in the prompt) also lands in Phase 2 NEW.

**In code (Clusters G + H).**

| File | What it provides |
|---|---|
| `src/fingym/memory/schema.py` | `MemoryArtifact`, `PromotionCheckResults`, `HeldOutReplayResult`, `CrossModelRegressionResult`, `SurvivorshipCheckResult`, `DomainOfValidity`, `AuditEntry` (Phase 0 deliverable; reused unchanged) |
| `src/fingym/memory/promotion.py` | `Proposal` dataclass + `evaluate_proposal_cross_model(proposal, scoreboard, min_variants_passing) -> MemoryArtifact \| None`. Returns L3 if checks 1+2+4 pass; L2 if check 1 passes for ≥1 variant + check 4 passes but check 2 doesn't reach the threshold; None otherwise |
| `src/fingym/memory/storage.py` | `save_promoted_skill` (L3) + `save_probationary_skill` (L2) + `load_promoted_skills` + `load_probationary_skills` + `render_for_system_prompt`. YAML round-trip |
| `src/fingym/memory/revalidation.py` | `revalidate(scoreboard, l3_dir, l2_dir, min_variants_passing)` runs the gate on every existing artifact; promotes / demotes / retires per the table above |
| `src/fingym/memory/population.py` | `LlmAgentVariant` + `DEFAULT_VARIANTS` + `build_population(variants, promoted_skills)` factory |
| `src/fingym/llm/anthropic.py` | Extended `AnthropicClient` accepts `prompt_style` field |
| `src/fingym/toys/llm_agent.py` | `LlmAgent` accepts `promoted_skills`; renders into system prompt |

**One sentence.** The promotion gate in toy mode (post-Cluster-H) runs checks 1, 2, and 4 with real evaluation against the multi-variant Scoreboard — check 2 counting how many of the population's variants independently confirm a tag is high-signal — and L2 / L3 / retirement transitions flow through re-validation cycles that fire every 50 new Scoreboard rows.

---

*Higher layers (2 through Apex) are itemized stone-by-stone in the table of contents at the top of this document. Detailed summaries land here as each stone is taught.*
