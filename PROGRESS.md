# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 1 NEW — Toy Architecture Extension (Weeks 3–6)**

Status: **opening** — Phase 0 closed 2026-05-16 with all 8 substeps green, all 4 exit criteria met, and the phase-gate audit passed.

The original BUILD.md plan had Phase 1 = data spine + real-data ingest. That sequencing has been reordered (see [DECISIONS.md](DECISIONS.md) "Constitution tightening v4: Phase 1 reorder"). Phase 1 NEW extends the synthetic_market toy *upward through the full architecture* before any real data is ingested. Each architectural piece — market-implied belief recovery, action layer, cost models, multi-horizon scoring, PIT discipline + restatements + delisted analogs, LLM-driven agent, memory + promotion gate, population mechanic — gets built and validated against the toy world FIRST. Real data substitutes into the toy-trained architecture in Phase 2 NEW, one data type at a time.

The reorder preserves the tight-stones cadence from Phase 0, exercises every load-bearing architectural piece under controlled inputs (S_true is known; the labelling function is ours; restatements and delistings are simulated), and defers vendor decisions until the architecture is proven. Synthetic data still **cannot validate alpha** (per DESIGN.md Three Arenas) — that requires real data. But synthetic CAN validate every other architectural property.

See [BUILD.md Phase 1](BUILD.md#phase-1--toy-architecture-extension-weeks-36) for the full phase definition.

---

## Phase 1 NEW — 8 clusters

| Cluster | Architecture piece (in toy mode) | PYRAMID stones touched | Status |
|---|---|---|---|
| **A** | Market-implied belief recovery — toy "market" emits prices derived from its belief; agent inverts price → recovers `P_market` | Stone 31 | ⬜ |
| **B** | Action layer + decision quality — agent picks long/short/NoAction from belief + gap; Stone 13 coherence checks fire | Stones 13 (code), 32 | ⬜ |
| **C** | Cost models + capacity — per-name liquidity + spread + impact + alpha decay; Stone 14 realized-edge column | Stone 14 (code) | ⬜ |
| **D** | Multi-horizon scoring — toy emits labels at multiple tick horizons; one Contract scored at all | Stone 10 (code) | ⬜ |
| **E** | PIT discipline + restatements + delisted analogs — toy emits restatement events (different `as_known`); toy companies "delist" mid-trajectory | Stones 24, 26 (in toy) | ⬜ |
| **F** | LLM-driven agent — first real LLM (Anthropic SDK) reads toy emissions as text, emits Contracts | Stone 30 (first instantiation) | ⬜ |
| **G** | Memory + promotion gate — LLM agent emits `memory_update_proposal` fields; toy promotion gate runs the four checks | Stones 39, 40 (in toy) | ⬜ |
| **H** | Population mechanic — 3 LLM-agent variants (different priors × prompts × memory subsets); scored in parallel | Stone 38 (in toy) | ⬜ |

Each cluster is ~3-4 tight sub-stones. Concept-in-chat first, then code, then verify — same texture as Phase 0. Total: ~24-27 sub-stones across Phase 1 NEW.

## Phase 1 NEW Exit Criteria

- All scoreboard columns populated (Brier, log_score, belief_delta_on_truth, decision_quality, realized_edge, reliability_buckets, mean_gap_on_truth); each tested against adversarial agents in the extended toy.
- LLM-driven agent produces valid Contracts (`contract_validator` accepts).
- Toy promotion gate produces L2 → L3 promotions on the toy `memory_registry`; LLM agents read promoted skills at session start.
- Population of ≥3 LLM agents runs in parallel with documented diversity in beliefs / actions.
- Trajectory store schema instantiated with toy Contracts; ready for the year-2 SFT format.
- All Phase 0 tests still green; mypy strict clean across all source files.

Phase 1 NEW exits when the full architecture has been exercised end-to-end in toy mode.

---

## Next Action

Next: **Cluster A — Market-implied belief recovery in the toy.** Concept-in-chat first, then code, same cadence as Phase 0.

The conceptual question: what does "market price" mean structurally in our toy world? The 3-state synthetic market already has a market believer (Stone 15 step 3) with its own belief over `{strg, stbl, dec}`. Cluster A turns that belief into an observable PRICE, then has the agent invert the price to recover `P_market`. This is Stone 31 in PYRAMID — implied DCF / options-implied probabilities / implied volatility in production; in toy mode, a simpler price-from-belief function.

Sub-stones for Cluster A (drafted; refine during teach-in-chat):

- **31a** — Concept: what is a price as a compression of belief? Worked example with concrete numbers.
- **31b** — Implement the toy market that emits a price each tick (derived from its current belief × payoff scaling).
- **31c** — Implement the belief-from-price inversion. Agent reads price stream → recovers `P_market`.
- **31d** — Wire `market_implied_belief` + `belief_delta` into Contracts emitted by this richer toy. Verify the validator accepts.

**No vendor decisions needed for Phase 1 NEW.** Vendor / corpus / SEC EDGAR / FMP-vs-Massive choices defer to Phase 2 NEW. The toy extension runs entirely on synthetic data; the Anthropic API key (Cluster F) is the only external integration during Phase 1 NEW.

---

## Phase 2 NEW preview — real-data transition

After Phase 1 NEW closes, Phase 2 NEW substitutes real data into the toy-trained architecture, one data type at a time. The seven previously-Phase-1 deliverables become Phase 2 NEW:

| Stone (PYRAMID) | Phase 2 NEW work |
|---|---|
| Stone 22 — Corpus QA on existing 10-year / 1700-name transcript corpus | First real-data step |
| Stone 23 — Six-data-type schema instantiated with real data | Schema validates against architecture |
| Stone 24 — PIT discipline at production scale | `time_leak_guard` fires on real timestamps |
| Stone 25 — Replay vs live parity | Same code path, real data |
| Stone 26 — Delisted shadow universe (real vendor) | SEC EDGAR cross-reference for delisted CIKs (per the FMP/Massive smoke-test findings) |
| Stone 27 — Trajectory store with real Contracts | Schema migrated; sample reads/writes cleanly |
| Stone 28 — Raw-evidence channel | Real data pipe operational |

Phase 2 NEW exit criterion: the toy-trained architecture works on real data end-to-end for at least one historical episode of one company.

---

## Completed Phases

### Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2) ✅ Closed 2026-05-16

**Substeps 1–8, all green:**

1. **Bootstrap engineering scaffolding** — `uv init`, `pyproject.toml`, ruff + mypy strict + pytest, pre-commit installed; 15 hooks green.
2. **Neon database** — Postgres 17.8 in `aws-eu-west-2`, alembic baseline `34760aee56bf` applied; `.env` populated.
3. **Migrate `toys/coin.py`** under mypy strict; PEP 695 type aliases over `Literal` for the closed alphabet.
4. **Build evaluator v0** — `brier`, `log_score`, `belief_delta_on_truth` (Stone 11a) in `src/fingym/evaluator/scoring.py`; `reliability_buckets` + `ReliabilityBucket` (Stone 18). Stone 15 synthetic-market toy (`src/fingym/toys/synthetic_market.py`) — world + believer + two-believer + scoreboard reproduction of PYRAMID Stone 11a's worked example. **Remaining scoreboard columns** (calibration curve, process-quality, decision-quality, capacity-adjusted; multi-horizon + expression_type tagging infrastructure) wait for their input machinery — most are now scheduled in Phase 1 NEW (clusters B/C/D).
5. **Adversarial test agents + ranking lock + reliability diagrams** — Stones 16-18. `src/fingym/toys/adversarial_agents.py` (ConfidentAgent, UniformAgent, BayesianAgent satisfying typed `Agent` Protocol); `tests/integration/test_evaluator_ranks_adversaries.py` (5 ranking tests); `src/fingym/toys/reliability_diagrams.py` (plotly HTML at `notebooks/reliability_diagrams.html`); `tests/integration/test_reliability_diagrams.py` (5 structural-shape tests).
6. **Model interface contract** — Stone 19. `src/fingym/agents/contract.py` (pydantic Contract + 11 nested types per CONTRACT.md), `src/fingym/agents/interface.py` (`Agent[Evidence]` Protocol, PEP 695 generic), `src/fingym/agents/contract_validator.py` (six Phase 0 validation checks), `src/fingym/toys/contract_emitter.py` (BayesianContractEmitter stub proves Protocol compiles). 20 unit tests.
7. **Memory artifact schema** — Stone 20. `src/fingym/memory/schema.py` (pydantic MemoryArtifact for L2/L3 per memory-design.md; 7 nested types; L3 invariant enforced); illustrative L3 sample in `memory_registry/promoted/`. 12 unit tests. `pyyaml` + `types-pyyaml` added as dev deps; pydantic mypy plugin enabled under `[tool.mypy]`.
8. **Property tests for math invariants** — Stone 21. `tests/property/test_math_invariants.py` with 8 hypothesis-based tests: Bayesian update commutativity (coin + 3-state), Brier and log_score properness in expectation, belief_delta signed-inverse + cross-state sum-to-zero, reliability_buckets count invariant, Brier-zero-on-degenerate-correct.

**All four Phase 0 exit criteria met:**

- ✅ Evaluator correctly orders adversarial agents on every scoreboard dimension.
- ✅ Reliability diagrams show overconfidence in confidently-wrong agent and zero discrimination in always-50% agent.
- ✅ Model interface contract documented; stub agent compiles against it.
- ✅ Memory schema documented and validates a sample skill artifact.

**Constitution tightening events during Phase 0** (see [DECISIONS.md](DECISIONS.md)):

- **v1**: `derived_features` → `derived_evidence` rename; physics-not-alpha sharpening of #5; trajectory-as-audit-object clarification + BIAS_PATTERN #11 (narrative as evidence); `no_alpha_features.py` lint added.
- **v2**: four-thing decomposition vocabulary (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`); DESIGN.md #2 sharpened with price-as-adversarial-belief; NO-EDGE elevated to Operational Constraint; CONTRACT.md created; PYRAMID Stone 11a + Stone 19 sharpened; BIAS_PATTERN #12 (trade-for-trade's-sake); stone-numbering convention.
- **v3**: one-sentence definition (CLAUDE.md + DESIGN.md); "Three Arenas" section in DESIGN.md; "What this system is NOT" anti-list in DESIGN.md Out of Scope; Worldlets concept parked in DECISIONS.md as **FUTURE RESEARCH, NOT COMMITTED**.
- **v4** (post-Phase-0, pre-Phase-1): Phase 1 reorder. Toy-extension first; real-data ingest moves to Phase 2 NEW. See DECISIONS.md.

**Final-state metrics:**

- **Tests**: 92 unit + 10 integration + 8 property + 22 lint = **132 green**; mypy strict clean across 31 source files.
- **Commits this phase**: Phase 0 spans the build history from initial scaffolding through `8a3205e` (Stone 21) plus session-coda transitions.
- **Two architectural questions parked** in DECISIONS.md (emission-triggered vs agent-driven Contract emission, leaning A; emissions taxonomy must include macro/sector/cross-asset). Revisit trigger: Phase 2 NEW (Stone 22-23 territory) — when real emissions are about to be ingested.

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

When a phase closes, move its details into "Completed Phases" as a condensed summary; details remain recoverable from git history and DECISIONS.md.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
