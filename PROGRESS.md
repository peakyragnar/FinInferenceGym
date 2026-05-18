# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 1 NEW — Toy Architecture Extension (Weeks 3–6) — under Constitution v5**

Status: **Clusters A + B complete (both 2026-05-18); Cluster C 14-a (teach + distill) ✅ (2026-05-18); next is 14-b (replace ToyCostModel with structured cost components + add `src/fingym/evaluator/realized_edge.py`).** Phase 0 closed 2026-05-16. Constitution v5 reformulated commitment #2 and restructured the Phase 1 NEW cluster sequence (see [DECISIONS.md "Constitution tightening v5"](DECISIONS.md) and [CONSTITUTION_V5_PLAN.md](CONSTITUTION_V5_PLAN.md)). Cluster A (single-believer toy + Forecast Ledger MVP) and Cluster B (calibration shrinkage + Tradable-Edge Action Engine + end-to-end pipeline lock-in) both shipped 2026-05-18. PYRAMID Stones 11b / 11c / 11d distilled; integration test at `tests/integration/test_cluster_b_pipeline.py` locks the three-agent crush (Confident NoAction post-shrinkage; Uniform always NoAction; Bayesian mixed; counterfactual confirms Stone 11c is load-bearing). Cluster C 14-a distilled into PYRAMID Stone 14 body (replaces "v5 reframing pending" marker) and FORMULAS Stone 14 entry (replaces parked entry). 147 tests green; mypy strict clean across 26 source files; pre-commit 15 hooks clean.

The original BUILD.md plan had Phase 1 = data spine + real-data ingest. That sequencing was reordered (v4, see [DECISIONS.md](DECISIONS.md) "Constitution tightening v4: Phase 1 reorder") and then reformulated (v5). Phase 1 NEW extends the synthetic_market toy *upward through the full architecture* before any real data is ingested. Each architectural piece — Forecast Ledger MVP, calibration shrinkage, Tradable-Edge Action Engine, cost models, multi-horizon scoring, PIT discipline + restatements + delisted analogs, LLM-driven agent, memory + promotion gate, population mechanic, Market-State Baseline isolation — gets built and validated against the toy world FIRST. Real data substitutes into the toy-trained architecture in Phase 2 NEW, one data type at a time.

The reorder preserves the tight-stones cadence from Phase 0, exercises every load-bearing architectural piece under controlled inputs (the toy emits realized returns; the labelling function is ours; restatements and delistings are simulated), and defers vendor decisions until the architecture is proven. Synthetic data still **cannot validate alpha** (per DESIGN.md Three Arenas) — that requires real data. But synthetic CAN validate every other architectural property.

See [BUILD.md Phase 1](BUILD.md#phase-1--toy-architecture-extension-weeks-36) for the full phase definition.

---

## Phase 1 NEW — 9 clusters (under v5)

| Cluster | Architecture piece (in toy mode) | PYRAMID stones touched | Status |
|---|---|---|---|
| **A** | Single-believer toy refactor + Forecast Ledger MVP — toy emits realized returns; agent forecasts a distribution; Ledger records each (forecast, realized return) pair indexed by signal class and computes per-signal-class reliability | Stones 7b, 11b | ✅ (2026-05-18) |
| **B** | Calibration shrinkage + Tradable-Edge Action Engine — per-signal-class reliability shrinks the raw forecast; Action Engine computes calibrated expected utility under Kelly and gates on margin-of-safety threshold | Stones 11c, 11d | ✅ (2026-05-18) |
| **C** | Cost models + capacity — per-name liquidity + spread + impact + alpha decay; Stone 14 realized-edge column | Stone 14 (code) | ⬜ |
| **D** | Multi-horizon scoring — toy emits realized returns at multiple tick horizons; one Contract scored at all | Stone 10 (code) | ⬜ |
| **E** | PIT discipline + restatements + delisted analogs — toy emits restatement events (different `as_known`); toy companies "delist" mid-trajectory | Stones 24, 26 (in toy) | ⬜ |
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

Next: **Phase 1 NEW Cluster C sub-stone 14-b — replace `ToyCostModel` with structured cost components + add `src/fingym/evaluator/realized_edge.py`.** 14-a is complete (PYRAMID Stone 14 body + FORMULAS Stone 14 entry distilled). 14-b replaces `ToyCostModel`'s single `round_trip_cost: float` field with structured fields (`adv`, `spread_bps`, `commission_bps`, `impact_coefficient`, `alpha_decay_bps_per_period`) plus a `round_trip_cost_at(notional, horizon_periods) -> float` method that the Action Engine calls; adds `src/fingym/evaluator/realized_edge.py` with the per-Contract backward-looking computation; migrates the ~10 existing Action Engine tests to the structured constructor. After 14-b, 14-c runs the integration test against the full adversarial-agent pipeline including realized_edge computation; Cluster C closes.

Draft sub-stones for Cluster C (refined during teach-in-chat):

- **14-a** ✅ (2026-05-18) — Concept + distill. Per-Contract `realized_edge = nominal_payoff − spread − commission − market_impact(size, ADV) − alpha_decay`, where `nominal_payoff = realized_return × direction × notional` (backward-looking; distinct from Stone 11d's forward-looking `calibrated_expected_utility`). Square-root impact law: `impact = impact_coefficient × sqrt(size / ADV)`. NoAction Contracts: `realized_edge = 0`. Sliced primarily by deployable size bucket; near-tautological structural check: mean realized_edge at the agent's stated size, across many trades, must be > 0. Distilled into PYRAMID Stone 14 body (replaces "v5 reframing pending" marker) with the decomposition table, sqrt-law worked table, size-bucket comparison table, and three properties (backward- vs forward-looking; column-level near-cap; sqrt impact is load-bearing). FORMULAS Stone 14 entry replaces the parked entry with the full decomposition, direction sign convention, square-root impact formula, properties, and Stone-11d connection.
- **14-b** — Replace `ToyCostModel` (currently `dataclass(round_trip_cost: float)`) with structured fields (`adv`, `spread_bps`, `commission_bps`, `impact_coefficient`, `alpha_decay_bps_per_period`); add a `round_trip_cost_at(notional, horizon_periods) -> float` method. Update `src/fingym/action/action_engine.decide(...)` to call `cost_model.round_trip_cost_at(notional, horizon_periods)` for the forward-looking utility — but at decision time `notional` is itself a function of the Kelly fraction, so the structure becomes: estimate notional under unit Kelly to derive provisional costs, then size with full Kelly; or: iterate. Document the choice. Add `src/fingym/evaluator/realized_edge.py` with `realized_edge(action, realized_return, cost_model, horizon_periods) -> float`. Migrate the ~10 existing Action Engine tests to the new constructor (replacing `ToyCostModel(round_trip_cost=0.01)` with structured equivalents that produce the same effective round-trip cost at the relevant size).
- **14-c** — End-to-end verification with adversarial agents. Run the full pipeline `toy → forecast → Ledger → shrink → decide → realized_edge` over many episodes; assert: BayesianAgent's aggregate `mean(realized_edge | size_bucket="small")` is positive; same agent at large size has degraded edge (sqrt-law fires); ConfidentAgent's NoActions all carry `realized_edge = 0` exactly; sqrt-law monotonicity holds across size buckets for a synthetic +3% trade. After 14-c, Cluster C closes; next cluster is D (multi-horizon scoring with realized_edge per horizon, Stone 10 in code).

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
