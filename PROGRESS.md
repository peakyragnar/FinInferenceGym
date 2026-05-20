# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 2 NEW — Real-Data Substitution (Weeks 7–10)**

Status: **Steps 1–7 complete (2026-05-19 → 2026-05-20). The full Phase 2 NEW end-to-end loop runs on real data with Track C attribution working.** Only the scaled replay (Step 8) remains before the architecture has statistically meaningful per-signal-class reliability + Track C numbers.

**Headline result — first real Track C attribution on real data:**

```
agent_id                      n_matured  mean_log_return
real_llm_v1                           6           +0.16%
market_state_baseline_real            5           -6.22%
```

**Incremental AI edge ≈ +6.4 percentage points** on the 5-pair test sample. Statistically weak at n=5 but the architectural signal is loud — the AI Core's value comes from refusing to trade SIVB Feb 2023 (NoAction, 75% probability of below_-5% returns) when the macro-only Baseline went LONG SIVB into the collapse. This is the DESIGN.md #2 commitment ("incremental AI edge over a macro-only control") **measured for the first time on real data**.

Phase 2 NEW substitutes real data into the toy-trained architecture, **one data type at a time** (per BUILD.md Phase 2, [DECISIONS.md Constitution v4](DECISIONS.md)). The toy never validated alpha (DESIGN.md Three Arenas); the real loop does. The deterministic-first ingest discipline ([real_data_ingest.md](real_data_ingest.md)) restricts Phase 2 NEW Stage 1 to data that requires no curation choices — prices, splits, dividends, ticker reference, IPOs. Fundamentals / news / transcripts each become their own subsequent stage with an explicit design pass.

See [BUILD.md Phase 2](BUILD.md#phase-2--real-data-transition-weeks-710) for the full phase definition; see [real_data_ingest.md](real_data_ingest.md) for the per-stage ingest plan.

---

## Phase 2 NEW — stones and status (post Steps 1–7)

| Stone | What | Status |
|---|---|---|
| **23 — headline_observables slice** | Real macro substrate from FRED in `headline_observables` Postgres table; 32 series, 202,672 rows; daily/weekly/monthly/quarterly cadence; ALFRED PIT verified on CPIAUCSL + PAYEMS first-prints | ✅ (2026-05-19) |
| **23 — equity deterministic tables** | `equity_prices` (15,649 bars), `corporate_actions_splits` (11), `corporate_actions_dividends` (231), `tickers` (active + delisted), `ipos`; survivorship-clean (SIVB collapse window captured, TWTR pre-buyout captured); 7-ticker test universe | ✅ (2026-05-20) |
| **23 — contracts trajectory store** | `contracts` table with denormalized scalars + JSONB Contract for round-trip; 16 Contracts persisted so far across AI Core + Baseline | ✅ (2026-05-20) |
| **23 — emissions table** | Rich event-shaped table (`emissions`) with surprise/consensus/scope metadata; requires consensus vendor (Trading Economics or similar) | ⬜ deferred — vendor decision pending |
| **23 — fundamentals table** | Long-table `(ticker, period, statement_type, line_item, vintage)` from Massive Developer legacy combined endpoint; design pass required first | ⬜ Stage 2 of real_data_ingest.md |
| **11e (real data)** | RealMarketStateBaseline reads from `headline_observables` (7-series narrow subset); trains in 3.1s; emits Contracts to trajectory store; Track C attribution computing | ✅ (2026-05-20) |
| **22** | Corpus QA on existing 10-year / 1700-name transcript corpus | ⬜ resequenced — deferred behind structured-first scope |
| **24** | PIT discipline at production scale (`time_leak_guard` on real timestamps; restatements via ALFRED) | ⬜ partial — ALFRED PIT first-print verified; `as_of`-anchored PIT for non-revised market series; full vintage tracking deferred |
| **25** | Replay vs live parity (byte-identical output) | ⬜ deferred to Phase 3 |
| **26** | Delisted shadow universe (real vendor) | ✅ on Massive Developer within 10-year window (SIVB, TWTR confirmed); SEC EDGAR pre-2016 cross-reference deferred |
| **27** | Trajectory store with real v5 Contracts | ✅ — `contracts` table populated; round-trip via pydantic verified |
| **28** | Raw-evidence channel operational (typed pipe delivering full unprocessed evidence) | ✅ for deterministic data (macro + prices + corporate actions + ticker reference); text body deferred to Stage 4+ |

**Vendor landscape (current)**:
- ✅ **FRED** (free) — macro substrate live, 32 series, 202K rows
- ✅ **Massive Developer** (already subscribed, $79/mo) — equity prices + corporate actions + ticker reference for 7-name test universe; 15,649 rows + 244 events
- ✅ **Anthropic API** (Haiku 4.5) — emitting real v5 Contracts via tool-call structured output
- ⬜ **Massive Advanced + Benzinga** — gated behind successful Stage 1 validation (now done); ~$500/month-1 burst for fundamentals + Form 4/13-F/short interest + analyst data
- ✗ **HY OAS / IG OAS** — ICE licensed long history away in May 2023; defer
- ✗ **Gold spot, MOVE, VIX term, ISM PMI, consensus/surprise** — separate vendor decisions deferred

## Phase 2 NEW Exit Criteria

Per BUILD.md Phase 2: the toy-trained architecture works on real data end-to-end for at least one historical episode of one company, including incremental AI edge measurement vs the real-data Market-State Baseline. Transcript corpus QA complete (passed clean or scoped to clean subset). Replay matches live byte-for-byte. Delisted shadow universe ingested and queryable. Trajectory store contains real v5 Contracts. All Phase 1 NEW tests still green.

---

## Next Action

**Step 8 — scaled replay.** The loop is structurally complete; what remains is volume. Run both agents on a monthly decision schedule across the 7-ticker test universe over ~10 years available history:
- ~840 (ticker, decision_date) pairs per agent (~120 monthly decisions per ticker × 7 tickers)
- AI Core: ~840 LLM calls (~$5–20 with Haiku 4.5; less with prompt caching)
- Baseline: ~840 instant calls ($0)
- ~30–45 min wall-clock
- Result: per-signal-class reliability tables fill statistically; Track C attribution becomes a real number rather than n=5 anecdote

After Step 8 the dashboard will show whether the AI Core's +6.4pp Track C edge holds up with real sample size. That's the architectural payoff.

Alternative — inspect current state before scaling:

```bash
# Train Baseline + emit Baseline Contracts on 5 test pairs (no LLM cost)
uv run --env-file .env python -m fingym.baseline.replay

# Run AI Core on same 5 pairs
uv run --env-file .env python scripts/run_replay_tiny.py

# See the full operator dashboard
uv run --env-file .env python -m fingym.operator real-report
```

### What shipped in Phase 2 NEW Steps 1–7 (2026-05-19 → 2026-05-20)

Commit chain (all on `origin/main`):

| Step | Commit | What landed |
|---|---|---|
| Docs | `b3ff2d0`, `feb514b` | [real_data_ingest.md](real_data_ingest.md) — formalized 8-stage ingest plan, deterministic-first scope, 7-ticker test universe (AAPL, JPM, TSLA, NVDA, VST + SIVB, TWTR) |
| Stage 0 | `5db188e` | FRED macro substrate (32 series, 202,672 rows) |
| Stage 1 | `12ef530` | Migration `c8d7e2a91f44` + Massive Developer ingest: 15,649 OHLCV bars, 11 splits, 231 dividends, 7 ticker references, 2 IPO records, survivorship-clean for SIVB + TWTR delisting windows |
| Step 1 | `c43bfb4` | RealMarketStateBaseline + `_load_macro_state`/`_load_ticker_prices` queries + batched 3.1s training over 7-name universe + 15,496 obs / 20 cells populated |
| Step 2 | `1c3b1b3` | RealLlmAgent — first real v5 Contract emitted on AAPL 2025-06-01 (signal_class_id `large_cap_tech_moderate_vol_recovery`); PIT correction (`as_of`-anchored macro filter) |
| Step 3 | `9529d7d` | Migration `d3f9c47b2a01` + `contracts` table + persistence module; round-trip verified (5/5 fields, pydantic model_validate) |
| Step 4 | `4988b2e` | Replay orchestrator; 5-pair smoke run; LLM invented 5 distinct signal_class_ids per decision context |
| Step 5 | `f620079` | `operator.real_report` CLI — trajectory store on a dashboard |
| Step 6 | `7b75a58` | Forecast Ledger reliability view + realized-edge-per-agent query; dashboard sections [3] and [4] live |
| Step 7 | `9c25577` | RealBaselineAgent + `fingym.baseline.replay` entry point (lives inside `src/fingym/baseline/` to respect the no-baseline-imports isolation rule); Track C attribution real on 5-pair sample |

**Test universe locked in for Stage 1**: AAPL, JPM, TSLA, NVDA, VST + SIVB (delisted 2023-03-28) + TWTR (delisted 2022-10-31). Sector diversity (tech / financial / auto-EV / semis / utility) + two distinct delisting mechanisms (bank failure + go-private).

**Architectural commitments preserved through Phase 2 NEW**:
- DESIGN.md #2: forecast distribution over realized returns, calibrated empirically — Forecast Ledger reliability view fills as Contracts mature to horizon
- DESIGN.md #3: time one-way valve — `as_of`-anchored PIT for non-revised market series, ALFRED first-print for revised macro emissions
- DESIGN.md #5: cognition/verification boundary — RealLlmAgent emits Contracts (cognition); contracts table + Forecast Ledger view (verification)
- DESIGN.md #6: raw-evidence native reasoning — AI Core reads prices + macro + corporate actions + ticker reference as natural-language prose; no pre-engineered features
- DESIGN.md #8: two-axis improvement — trajectory store live in SFT-fit JSONB format from first Contract
- PYRAMID Stone 11e: Baseline isolation — `mechanisms/lints/no_baseline_imports.py` correctly blocked scripts/ from importing `fingym.baseline`, forced orchestration inside the package

**Vendor cost so far**: $79/month (existing Massive Developer subscription) + Anthropic API at ~$0.01 per LLM call. Stage 1 ingest + Step 4 + Step 7 baseline replays together: <$1 in API spend.

---

## Completed Phases

### Phase 1 NEW — Toy Architecture Extension ✅ Closed 2026-05-18

9 clusters (A–I), 245 tests green, mypy strict across 41 source files, 16 pre-commit hooks, operator dashboard live.

| Cluster | What landed | Stones |
|---|---|---|
| A | Single-believer toy refactor + Forecast Ledger MVP | 7b, 11b |
| B | Calibration shrinkage + Tradable-Edge Action Engine | 11c, 11d |
| C | Cost models + capacity (Stone 14 realized-edge column) | 14 |
| D | Multi-horizon scoring | 10 |
| E | PIT discipline + restatements + delisted analogs (toy mechanism) | 24, 26 |
| F | First LLM-driven agent (Anthropic SDK, Haiku 4.5) | 30 |
| G | Memory + promotion gate (checks 1+4 real; 2+3 stubbed) | 39, 40 |
| H | Population variants + real cross-model regression (check 2 real; 3 still stubbed) | 38, 40 (extended) |
| I | Market-State Baseline isolation + incremental_AI_edge attribution (toy mechanism) | 11e |

**Post-close work (also 2026-05-18 / 2026-05-19)**: v5 vocab cleanup + Phase 1 NEW retrospective consolidation; operator dashboard module (`src/fingym/operator/` + JSONL scoreboard persistence) for the auditor's inspectability surface per DESIGN.md #10.

**Phase 1 NEW closing-state metrics**: 239 tests + 6 operator-dashboard / vocab-cleanup tests = 245 green; mypy strict clean across 41 source files; 16 pre-commit hooks clean.

**Two architectural questions parked** in DECISIONS.md (emission-triggered vs agent-driven Contract emission, leaning A; emissions taxonomy must include macro/sector/cross-asset). Both reopen during Phase 2 NEW Stone 23 / emissions-table work — the materiality logic stone is the natural resolution point.

Full detail of each cluster is recoverable from git history (commits `5db188e`…`c7bf4e9`) and from DECISIONS.md tightening v4 + v5 entries.

### Phase 0 — Evaluator + Model Interface Contract + Toys ✅ Closed 2026-05-16

All 8 substeps green (bootstrap, Neon DB, mypy-strict toy migration, evaluator v0, adversarial agents + ranking lock + reliability diagrams, Model interface Contract, memory artifact schema, property tests for math invariants). All 4 exit criteria met. Tests at close (pre-v5): 92 unit + 10 integration + 8 property + 22 lint = 132 green; mypy strict clean across 31 source files.

**Constitution tightening events** (see [DECISIONS.md](DECISIONS.md)): v1 (`derived_features` → `derived_evidence`, physics-not-alpha sharpening), v2 (four-thing decomposition vocabulary, CONTRACT.md created, NO-EDGE first-class), v3 (one-sentence purpose, Three Arenas section, anti-list, Worldlets parked), v4 (Phase 1 reorder — toy first, real data second), v5 (commitment #2 reformulated: forecast over realized returns, Forecast Ledger, Tradable-Edge Action Engine, isolated Market-State Baseline).

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

When a phase closes, move its details into "Completed Phases" as a condensed summary; details remain recoverable from git history and DECISIONS.md.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
