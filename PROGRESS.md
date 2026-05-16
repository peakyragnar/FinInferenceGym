# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 1 — Data Spine + Raw-Evidence Channel (Weeks 3–4)**

Status: **opening** — Phase 0 closed 2026-05-16 with all 8 substeps green and all 4 exit criteria met. Phase-gate audit passed: stop-the-line conditions (#1–#4) all clear; #5 evaluator-honesty verified by Stones 17/18/21 (adversarial ranking + reliability diagrams + property tests); #6–#8 are N/A pre-Phase-1; #9 budget/schedule confirmed by operator. Phase 1 covers corpus QA on the existing 10-year / 1700-name transcript dataset (Stone 22), then the data spine + raw-evidence channel + delisted shadow universe + trajectory store schema (Stones 23–28).

See [BUILD.md Phase 1](BUILD.md#phase-1--data-spine--raw-evidence-channel-weeks-34) for the full phase definition (teaching, build, design cross-reference, exit criterion, slippage watch).

---

## Phase 1 Checklist

| Deliverable | Status |
|---|---|
| Corpus QA on the existing 10-year / 1700-name transcript dataset (Stone 22) — stratified sample, statistical scan, spot-check | ⬜ Not started |
| Vendor selection + ingest pipelines: Norgate Premium (PIT fundamentals + prices, including delisted), IBKR (live + options), FRED (macro), existing transcript corpus | ⬜ Not started |
| Six-data-type schema (emissions / derived_evidence / beliefs / actions / labels / scores) with `as_of`, `as_known`, `source`, `version`, `corpus_bias` flag (Stone 23) | ⬜ Not started |
| Point-in-time discipline depth: `time_leak_guard`, look-ahead audits, restated-fact handling (Stone 24) | ⬜ Not started |
| Replay vs live pipeline parity (Stone 25) — same code path, byte-identical output | ⬜ Not started |
| Delisted shadow universe (Stone 26) — Norgate fundamentals + prices for delisted / bankrupt / acquired names | ⬜ Not started |
| Trajectory store in SFT-fit format (Stone 27) — per the Stone 19 Contract; ready for year-2 own-model fine-tune | ⬜ Not started |
| Raw-evidence channel (Stone 28) — typed pipe delivering full unprocessed evidence on demand | ⬜ Not started |

## Phase 1 Exit Criteria (from BUILD.md)

- Transcript corpus QA complete; either passed clean or scoped to a clean subset with documentation.
- Replay matches live byte-for-byte across multiple sample dates.
- No look-ahead leak passes adversarial test (as-of 2020-Q3 cannot reveal anything published in 2020-Q4 or later).
- Raw-evidence channel delivers full unprocessed evidence for any `(company, as_of_date)`.
- Delisted shadow universe is ingested and queryable; sample delisted-name retrieval works.
- Trajectory store schema is documented; a sample trajectory writes and reads cleanly.

---

## Next Action

Next: **Stone 22 — Corpus QA** on the existing 10-year / 1700-name transcript corpus. Phase 1's first substantive step. Per BUILD.md slippage watch: *"Are we tempted to skip corpus QA and start ingesting? No. Dirty data poisons everything downstream."*

Stone 22 deliverables:

1. **Stratified sample of ~30 transcripts** across companies / years / quarters. Manual read: speaker-tagging accuracy, Q&A delineation, timestamp correctness, missing sections, hallucinated content from speech-to-text errors.
2. **Statistical scan of all ~40K transcripts**: length distribution, missing fields, duplicate detection, company-name to CUSIP/ticker normalization.
3. **Spot-check against IR-website transcripts** for 5 names across the time window to verify accuracy.

Outcome possibilities (BUILD.md): corpus passes QA / corpus has fixable issues / corpus must be scoped to clean subsets. **We do not build on dirty data.**

**Operator-level prep before Stone 22 can run:**

- **Corpus access** — the 10-year / 1700-name transcript corpus needs to be wired into the build environment (local disk, cloud bucket, or other surface the repo can read).
- **Vendor decisions** (Phase 1 will land subsequent stones, but decide early): Norgate Premium subscription confirmed (~$200–500/month estimated; the largest line item in the $11–17K total budget). CBOE DataShop or OptionMetrics via WRDS for historical options. FRED API key for macro (free).
- **IBKR account** active (for the live feed later in Phase 1; can be deferred to Phase 3 if doing historical replay first).

After Stone 22 lands, Stones 23–28 build the data spine atop validated data. BUILD.md slippage watches for Phase 1 are explicit: no feature engineering creeping into the spine; no transcript summarization; no survivorship-bias smuggling (delisted shadow universe is part of every relevant validation); no trajectory format compromise; no corpus-QA skipping.

---

## Completed Phases

### Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2) ✅ Closed 2026-05-16

**Substeps 1–8, all green:**

1. **Bootstrap engineering scaffolding** — `uv init`, `pyproject.toml`, ruff + mypy strict + pytest, pre-commit installed; 15 hooks green.
2. **Neon database** — Postgres 17.8 in `aws-eu-west-2`, alembic baseline `34760aee56bf` applied; `.env` populated.
3. **Migrate `toys/coin.py`** under mypy strict; PEP 695 type aliases over `Literal` for the closed alphabet.
4. **Build evaluator v0** — `brier`, `log_score`, `belief_delta_on_truth` (Stone 11a) in `src/fingym/evaluator/scoring.py`; `reliability_buckets` + `ReliabilityBucket` (Stone 18). Stone 15 synthetic-market toy (`src/fingym/toys/synthetic_market.py`) — world + believer + two-believer + scoreboard reproduction of PYRAMID Stone 11a's worked example. **Remaining scoreboard columns** (calibration curve, process-quality, decision-quality, capacity-adjusted; multi-horizon + expression_type tagging infrastructure) wait for their input machinery — Phase 1's emissions table, Phase 2's action layer.
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

**Final-state metrics:**

- **Tests**: 92 unit + 10 integration + 8 property + 22 lint = **132 green**; mypy strict clean across 31 source files.
- **Commits this phase**: Phase 0 spans the build history from initial scaffolding through `8a3205e` (Stone 21).
- **Two architectural questions parked** in DECISIONS.md (emission-triggered vs agent-driven Contract emission, leaning A; emissions taxonomy must include macro/sector/cross-asset). Revisit trigger: Stone 22–23 (Phase 1).

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

When a phase closes, move its details into "Completed Phases" as a condensed summary; details remain recoverable from git history and DECISIONS.md.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
