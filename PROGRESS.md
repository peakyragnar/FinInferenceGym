# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 1 NEW — Toy Architecture Extension (Weeks 3–6) — under Constitution v5**

Status: **Clusters A + B + C + D + E all complete (all 2026-05-18). Cluster E E-a ✅, E-b ✅, E-c ✅. Next is Cluster F (LLM-driven agent, Stone 30 in toy mode — first real Anthropic SDK integration reading toy emissions as text).** Phase 0 closed 2026-05-16. Constitution v5 reformulated commitment #2 and restructured the Phase 1 NEW cluster sequence (see [DECISIONS.md "Constitution tightening v5"](DECISIONS.md) and [CONSTITUTION_V5_PLAN.md](CONSTITUTION_V5_PLAN.md)). Cluster D shipped 2026-05-18: `realize_returns_at_horizons` + `src/fingym/evaluator/scoreboard.py` + 8 integration tests pinning per-horizon scoring. Cluster E shipped 2026-05-18: PYRAMID Stones 24 + 26 bodies distilled into a new Layer 4 section (replaces TOC-only markers); `EmissionRecord` frozen dataclass + `time_leak_guard(records, query_tick)` function added to `src/fingym/toys/synthetic_market.py` for Stone 24 PIT discipline; `realize_returns_at_horizons` extended with keyword-only `delist_at` + `delist_payoff` parameters for Stone 26 delistings; 14 integration tests at `tests/integration/test_cluster_e_pipeline.py` pin time_leak_guard filtering / latest-per-as_of under restatements / sorted output / empty-under-early-query; concrete PIT scenario (Bayesian agent forecast differs before vs after a revision becomes visible); delisting payoff handling at horizon boundary / validation guards / backward-compat / both directions of trade direction; survivorship: Scoreboard preserves delisted rows with mean aggregation reflecting the losses. 194 tests green; mypy strict clean across 28 source files; pre-commit 15 hooks clean.

The original BUILD.md plan had Phase 1 = data spine + real-data ingest. That sequencing was reordered (v4, see [DECISIONS.md](DECISIONS.md) "Constitution tightening v4: Phase 1 reorder") and then reformulated (v5). Phase 1 NEW extends the synthetic_market toy *upward through the full architecture* before any real data is ingested. Each architectural piece — Forecast Ledger MVP, calibration shrinkage, Tradable-Edge Action Engine, cost models, multi-horizon scoring, PIT discipline + restatements + delisted analogs, LLM-driven agent, memory + promotion gate, population mechanic, Market-State Baseline isolation — gets built and validated against the toy world FIRST. Real data substitutes into the toy-trained architecture in Phase 2 NEW, one data type at a time.

The reorder preserves the tight-stones cadence from Phase 0, exercises every load-bearing architectural piece under controlled inputs (the toy emits realized returns; the labelling function is ours; restatements and delistings are simulated), and defers vendor decisions until the architecture is proven. Synthetic data still **cannot validate alpha** (per DESIGN.md Three Arenas) — that requires real data. But synthetic CAN validate every other architectural property.

See [BUILD.md Phase 1](BUILD.md#phase-1--toy-architecture-extension-weeks-36) for the full phase definition.

---

## Phase 1 NEW — 9 clusters (under v5)

| Cluster | Architecture piece (in toy mode) | PYRAMID stones touched | Status |
|---|---|---|---|
| **A** | Single-believer toy refactor + Forecast Ledger MVP — toy emits realized returns; agent forecasts a distribution; Ledger records each (forecast, realized return) pair indexed by signal class and computes per-signal-class reliability | Stones 7b, 11b | ✅ (2026-05-18) |
| **B** | Calibration shrinkage + Tradable-Edge Action Engine — per-signal-class reliability shrinks the raw forecast; Action Engine computes calibrated expected utility under Kelly and gates on margin-of-safety threshold | Stones 11c, 11d | ✅ (2026-05-18) |
| **C** | Cost models + capacity — per-name liquidity + spread + impact + alpha decay; Stone 14 realized-edge column | Stone 14 (code) | ✅ (2026-05-18) |
| **D** | Multi-horizon scoring — toy emits realized returns at multiple tick horizons; one Contract scored at all | Stone 10 (code) | ✅ (2026-05-18) |
| **E** | PIT discipline + restatements + delisted analogs — toy emits restatement events (different `as_known`); toy companies "delist" mid-trajectory | Stones 24, 26 (in toy) | ✅ (2026-05-18) |
| **F** | LLM-driven agent — first real LLM (Anthropic SDK) reads toy emissions as text, emits v5 Contracts | Stone 30 (first instantiation) | ⬜ |
| **G** | Memory + promotion gate — LLM agent emits `memory_update_proposal` fields; toy promotion gate runs the four checks | Stones 39, 40 (in toy) | ⬜ |
| **H** | Population mechanic — 3 LLM-agent variants (different priors × prompts × memory subsets); scored in parallel | Stone 38 (in toy) | ⬜ |
| **I** | Market-State Baseline isolation — separate `src/fingym/baseline/` module reads only toy headline observables; AI Core cannot import from `baseline/` (import-linter rule); incremental AI edge attribution column | Stone 11e (in toy) | ⬜ |

Each cluster is ~3-4 tight sub-stones. Concept-in-chat first, then distilled summary in PYRAMID, then code, then verify — same texture as Phase 0. Total: ~27-30 sub-stones across Phase 1 NEW.

## Phase 1 NEW Exit Criteria (under v5)

- All scoreboard columns populated (Brier, log_score, reliability_buckets, per-signal-class reliability from the Forecast Ledger, calibrated_expected_utility, tradable_edge_score, realized_edge after costs, incremental_AI_edge over Baseline); each tested against adversarial agents in the extended toy.
- LLM-driven agent produces valid v5 Contracts (`contract_validator` accepts cognition fields; Tradable-Edge Action Engine populates verification fields).
- Toy promotion gate produces L2 → L3 promotions on the toy `memory_registry`; LLM agents read promoted skills at session start.
- Population of ≥3 LLM agents runs in parallel with documented diversity in forecasts / actions.
- Toy Market-State Baseline runs in code-level isolation; `agents/` cannot import from `baseline/` (import-linter rule enforced); incremental AI edge column populated.
- Trajectory store schema instantiated with toy v5 Contracts; ready for the year-2 SFT format.
- All Phase 0 surviving tests still green; mypy strict clean across all source files.

Phase 1 NEW exits when the full architecture has been exercised end-to-end in toy mode.

---

## Next Action

Next: **Phase 1 NEW Cluster F — LLM-driven agent (Stone 30 in toy mode).** Cluster E closed 2026-05-18 with PIT discipline + delistings locked in. Cluster F replaces the hand-coded BayesianAgent with a frontier model reading toy emissions *as text* and emitting v5 Contracts via the Anthropic SDK. First real external integration (the Anthropic API key is the only external dependency in Phase 1 NEW). The LLM sees the emission stream as natural-language transcripts, forms a forecast over realized-return buckets, tags it with a `signal_class_id` of its own choosing, populates `recommended_action`, and the existing Stone 11c → 11d → 14 verification machinery scores it. After Cluster F, we'll have validated that the verifier behaves correctly under a real-model cognitive layer (still on toy data).

Cluster E (✅ 2026-05-18) sub-stones, kept here for the current-cluster pattern:

- **E-a** ✅ (2026-05-18) — Teach + distill. Combined teaching for Stones 24 (PIT discipline) + 26 (survivorship + delistings) since they share the `as_known` infrastructure. Distilled into PYRAMID as a new **Layer 4 — Real-data discipline (toy-first mechanisms)** section. Stone 24 body covers: two timestamps per record (`as_of` vs `as_known`); the PIT rule; restatements as append-only separate records; worked four-row table showing how a Bayesian agent at different query ticks sees different subsets; three properties (append-only audit, time_leak_guard as single mechanism, same code path synthetic + real); Cluster E in-code pointer. Stone 26 body covers: the survivorship hazard; the delisted-shadow-universe principle; `delist_at` + `delist_payoff` toy mechanism; worked multi-horizon table for a bankruptcy at tick 5; three properties (delisted stay in universe, payoff is labelling-function output, delistings stress-test the Stone 14 column-level check); Cluster E in-code pointer. Both TOC entries flipped from ⬜ to ✅ (toy mechanism).
- **E-b** ✅ (2026-05-18) — Built the toy extensions. `EmissionRecord` frozen dataclass added to `src/fingym/toys/synthetic_market.py` wrapping the existing `Emission` Literal alphabet with `as_of` + `as_known` PIT metadata; `time_leak_guard(records, query_tick) -> list[EmissionRecord]` returns the PIT view (filter by as_known, dedupe per as_of keeping latest, sorted output); `realize_returns_at_horizons` extended with keyword-only `delist_at` + `delist_payoff` params (post-delist horizons return the fixed payoff; backward-compat preserved when params omitted). Validation: `delist_at` without `delist_payoff` raises, and vice versa.
- **E-c** ✅ (2026-05-18) — Integration test at [tests/integration/test_cluster_e_pipeline.py](tests/integration/test_cluster_e_pipeline.py) (14 tests). Stone 24: time_leak_guard filters future records; picks latest per as_of under restatement; sorted output; empty under early query; handles multiple revisions per as_of; concrete agent-forecast-changes-after-restatement scenario. Stone 26: post-delist horizons return fixed payoff; boundary inclusive (h == delist_at counts as delisted); validation guards (delist_at without payoff raises; payoff without delist_at raises); backward-compat (no delist args = original behavior); both trade directions (long into bankruptcy = deeply negative, short into bankruptcy = deeply positive); Scoreboard preserves delisted rows so mean realized_edge reflects the losses (survivorship-bias guard).

After Cluster F, Clusters G-I are memory + promotion gate / population / Market-State Baseline isolation. Sub-stone drafts for each new cluster will be added as we approach them.

**No vendor decisions needed for Phase 1 NEW.** Vendor / corpus / SEC EDGAR / FMP-vs-Massive choices defer to Phase 2 NEW. The toy extension runs entirely on synthetic data; the Anthropic API key (Cluster F) is the only external integration during Phase 1 NEW.

### Cluster A (✅ 2026-05-18) — what shipped

- Single-believer toy refactor: agents emit forecasts over realized-return BUCKETS via bucket-conditional emission likelihoods (no hidden-state cognition by the agent). [src/fingym/toys/synthetic_market.py](src/fingym/toys/synthetic_market.py), [src/fingym/toys/adversarial_agents.py](src/fingym/toys/adversarial_agents.py).
- Forecast Ledger MVP: in-memory append-only `ForecastLedger`; read API `reliability_for_signal_class` returns per-claim-bucket reliability data. [src/fingym/ledger/forecast_ledger.py](src/fingym/ledger/forecast_ledger.py).
- 11 unit tests at [tests/unit/test_forecast_ledger.py](tests/unit/test_forecast_ledger.py); 7 end-to-end integration tests at [tests/integration/test_forecast_ledger_cluster_a.py](tests/integration/test_forecast_ledger_cluster_a.py).
- Printed inspection surface: `uv run python -m fingym.toys.ledger_demo` prints the three signal-class reliability tables. [src/fingym/toys/ledger_demo.py](src/fingym/toys/ledger_demo.py).
- Stone 11b distilled into PYRAMID Layer 2 body.

---

## Phase 2 NEW preview — real-data transition

After Phase 1 NEW closes, Phase 2 NEW substitutes real data into the toy-trained architecture, one data type at a time. The seven previously-Phase-1 deliverables become Phase 2 NEW:

| Stone (PYRAMID) | Phase 2 NEW work |
|---|---|
| Stone 22 — Corpus QA on existing 10-year / 1700-name transcript corpus | First real-data step |
| Stone 23 — Six-data-type schema instantiated with real data (v5 names: `emissions`, `derived_evidence`, `forecasts`, `actions`, `realized_returns`, `scores`; plus `headline_observables` and the Forecast Ledger view) | Schema validates against architecture |
| Stone 24 — PIT discipline at production scale | `time_leak_guard` fires on real timestamps |
| Stone 25 — Replay vs live parity | Same code path, real data |
| Stone 26 — Delisted shadow universe (real vendor) | SEC EDGAR cross-reference for delisted CIKs (per the FMP/Massive smoke-test findings) |
| Stone 27 — Trajectory store with real v5 Contracts | Schema migrated; sample reads/writes cleanly |
| Stone 28 — Raw-evidence channel | Real data pipe operational; includes raw `headline_observables` for both AI Core and Baseline |
| Stone 11e (real data) — Market-State Baseline on real headline observables | `src/fingym/baseline/` reads real rates/vol/FX/commodities; isolation rule still fires structurally; incremental AI edge column populated on real data |

Phase 2 NEW exit criterion: the toy-trained architecture works on real data end-to-end for at least one historical episode of one company, including incremental AI edge measurement vs the Market-State Baseline.

---

## Completed Phases

### Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2) ✅ Closed 2026-05-16

**Substeps 1–8, all green at close 2026-05-16:**

1. **Bootstrap engineering scaffolding** — `uv init`, `pyproject.toml`, ruff + mypy strict + pytest, pre-commit installed; 15 hooks green.
2. **Neon database** — Postgres 17.8 in `aws-eu-west-2`, alembic baseline `34760aee56bf` applied; `.env` populated.
3. **Migrate `toys/coin.py`** under mypy strict; PEP 695 type aliases over `Literal` for the closed alphabet.
4. **Build evaluator v0** — `brier`, `log_score` in `src/fingym/evaluator/scoring.py`; `reliability_buckets` + `ReliabilityBucket` (Stone 18). The synthetic-market toy (`src/fingym/toys/synthetic_market.py`) — world + single believer. The two-believer setup and `belief_delta_on_truth` were built in Phase 0 under pre-v5 framing; the v5 cleanup pass (2026-05-18) removed them and removed Stone 11a from PYRAMID. The single-believer skeleton survives and is the foundation for Phase 1 NEW Cluster A's Forecast Ledger MVP.
5. **Adversarial test agents + ranking lock + reliability diagrams** — Stones 16-18. `src/fingym/toys/adversarial_agents.py` (ConfidentAgent, UniformAgent, BayesianAgent satisfying typed `Agent` Protocol); `tests/integration/test_evaluator_ranks_adversaries.py`; `src/fingym/toys/reliability_diagrams.py` (plotly HTML at `notebooks/reliability_diagrams.html`); `tests/integration/test_reliability_diagrams.py`. Stones 16-18 survive v5 unchanged at the framing level; specific test assertions targeting `belief_delta_on_truth` are removed in the v5 cleanup.
6. **Model interface contract** — Stone 19. `src/fingym/agents/contract.py` (pydantic Contract per CONTRACT.md), `src/fingym/agents/interface.py` (`Agent[Evidence]` Protocol, PEP 695 generic), `src/fingym/agents/contract_validator.py` (Phase 0 validation checks), `src/fingym/toys/contract_emitter.py`. v5 cleanup pass: removed `market_implied_belief`, `belief_delta`, `hidden_state_hypotheses` fields and their nested types; renamed `ai_belief` → `forecast_distribution`; added v5 fields (`signal_class_id`, `thesis_category`, etc.) per the v5 CONTRACT.md spec.
7. **Memory artifact schema** — Stone 20. `src/fingym/memory/schema.py` (pydantic MemoryArtifact for L2/L3 per memory-design.md). Survives v5 unchanged at the schema level; promotion-gate metrics updated to reference Forecast Ledger reliability.
8. **Property tests for math invariants** — Stone 21. `tests/property/test_math_invariants.py` with hypothesis-based tests: Bayesian update commutativity (coin + 3-state), Brier and log_score properness in expectation, reliability_buckets count invariant, Brier-zero-on-degenerate-correct. The belief_delta property tests were removed in the v5 cleanup.

**All four Phase 0 exit criteria met at close 2026-05-16:**

- ✅ Evaluator correctly orders adversarial agents on every scoreboard dimension.
- ✅ Reliability diagrams show overconfidence in confidently-wrong agent and zero discrimination in always-50% agent.
- ✅ Model interface contract documented; stub agent compiles against it.
- ✅ Memory schema documented and validates a sample skill artifact.

**Constitution tightening events** (see [DECISIONS.md](DECISIONS.md)):

- **v1**: `derived_features` → `derived_evidence` rename; physics-not-alpha sharpening of #5; trajectory-as-audit-object clarification + BIAS_PATTERN #11 (narrative as evidence); `no_alpha_features.py` lint added.
- **v2**: four-thing decomposition vocabulary (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`); DESIGN.md #2 sharpened with price-as-adversarial-belief; NO-EDGE elevated to Operational Constraint; CONTRACT.md created; PYRAMID Stone 11a + Stone 19 sharpened; BIAS_PATTERN #12 (trade-for-trade's-sake); stone-numbering convention.
- **v3**: one-sentence definition (CLAUDE.md + DESIGN.md); "Three Arenas" section in DESIGN.md; "What this system is NOT" anti-list in DESIGN.md Out of Scope; Worldlets concept parked in DECISIONS.md as **FUTURE RESEARCH, NOT COMMITTED**.
- **v4** (post-Phase-0, pre-Phase-1): Phase 1 reorder. Toy-extension first; real-data ingest moves to Phase 2 NEW. See DECISIONS.md.
- **v5** (post-Phase-0, pre-Phase-1 NEW teaching): reformulated commitment #2 from "belief over hidden state with `P_market` recovery" to "forecast distribution over realized returns, calibrated empirically via the Forecast Ledger; action gated on calibrated expected utility clearing a margin of safety; isolated Market-State Baseline for attribution." Removed: four-thing decomposition, Stones 7a / 11a / 31, two-believer toy, `belief_delta` everywhere. Added: Stones 7b / 11b / 11c / 11d / 11e (full distilled summaries pending teaching), `src/fingym/ledger/` + `src/fingym/action/` + `src/fingym/baseline/` module specs, import-linter rule (`agents/ ↛ baseline/`). See DECISIONS.md and CONSTITUTION_V5_PLAN.md.

**Final-state metrics at Phase 0 close (2026-05-16, pre-v5):**

- **Tests**: 92 unit + 10 integration + 8 property + 22 lint = **132 green**; mypy strict clean across 31 source files.
- **Commits this phase**: Phase 0 spans the build history from initial scaffolding through `8a3205e` (Stone 21) plus session-coda transitions. Pre-v5 stable tag `v0.1` placed at commit `64df5a4` on 2026-05-18 as the return point.

**Post-v5-cleanup metrics:** updated at the end of the v5 cleanup pass (after code deletions and corresponding test removals). Stable tag `v0.2` will be placed at the post-v5-cleanup state once mypy / tests / pre-commit are all green.

**Two architectural questions parked** in DECISIONS.md (emission-triggered vs agent-driven Contract emission, leaning A; emissions taxonomy must include macro/sector/cross-asset). Revisit trigger: Phase 2 NEW (Stone 22-23 territory) — when real emissions are about to be ingested.

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

When a phase closes, move its details into "Completed Phases" as a condensed summary; details remain recoverable from git history and DECISIONS.md.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
