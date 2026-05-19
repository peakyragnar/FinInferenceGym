# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 2 NEW — Real-Data Substitution (Weeks 7–10)**

Status: **Started 2026-05-19.** Phase 1 NEW closed 2026-05-18 (all 9 clusters ✅, operator dashboard live, 245 tests green, mypy strict clean, 16 pre-commit hooks). Phase 2 NEW substitutes real data into the toy-trained architecture, **one data type at a time** (per BUILD.md Phase 2, [DECISIONS.md Constitution v4](DECISIONS.md)). The toy still cannot validate alpha (DESIGN.md Three Arenas); alpha validation begins here, on real data.

First Phase 2 NEW work landed 2026-05-19: **`headline_observables` slice of Stone 23** — real macro substrate from FRED. 202,672 rows across 32 series on Neon, vintage=1, current-vintage values. This unblocks Stone 11e real-data Baseline work and is the foundation for the broader Stone 23 canonical-schema rollout.

See [BUILD.md Phase 2](BUILD.md#phase-2--real-data-transition-weeks-710) for the full phase definition.

---

## Phase 2 NEW — stones and status

| Stone | What | Status |
|---|---|---|
| **23 — headline_observables slice** | Real macro substrate from FRED in `headline_observables` Postgres table; 32 series, 202,672 rows; daily/weekly/monthly/quarterly cadence; ALFRED PIT verified on CPIAUCSL + PAYEMS first-prints | ✅ (2026-05-19) |
| **23 — emissions table** | Rich event-shaped table (`emissions`) with surprise/consensus/scope metadata; requires consensus vendor (Trading Economics or similar) | ⬜ deferred — vendor decision pending |
| **23 — remaining tables** | `derived_evidence`, `forecasts`, `actions`, `realized_returns`, `scores`, Forecast Ledger view | ⬜ |
| **11e (real data)** | Real Market-State Baseline reads from `headline_observables` (narrow 7-series subset); incremental_AI_edge attribution on real data | ⬜ unblocked — substrate exists, Baseline not yet wired |
| **22** | Corpus QA on existing 10-year / 1700-name transcript corpus | ⬜ resequenced — was originally first Phase 2 NEW step; Michael's audit moved it after the data substrate so it can be evaluated against the broader pipeline |
| **24** | PIT discipline at production scale (`time_leak_guard` on real timestamps; restatements via ALFRED) | ⬜ partial — toy mechanism in place; real-data ALFRED vintage tracking deferred |
| **25** | Replay vs live parity (byte-identical output) | ⬜ |
| **26** | Delisted shadow universe (real vendor — SEC EDGAR for delisted CIKs) | ⬜ |
| **27** | Trajectory store with real v5 Contracts | ⬜ |
| **28** | Raw-evidence channel operational (typed pipe delivering full unprocessed evidence) | ⬜ |

**Vendor landscape after FRED smoke test (2026-05-19)**:
- ✅ **FRED** (free) — rates, vol (VIX only), FX, oil, breakevens, macro emissions (CPI/NFP/GDP/etc.) with ALFRED PIT first-print
- ✗ **HY OAS, IG OAS** — ICE licensed FRED's long history away in May 2023. Decision pending: pay ICE/Bloomberg, compute HYG-Treasury proxy, or accept 3-year history
- ✗ **Gold spot** — not on FRED. Yahoo `GC=F` (free) is the cleanest path
- ✗ **MOVE, VIX term structure, ISM PMI, consensus/surprise data** — separate vendor decisions deferred

## Phase 2 NEW Exit Criteria

Per BUILD.md Phase 2: the toy-trained architecture works on real data end-to-end for at least one historical episode of one company, including incremental AI edge measurement vs the real-data Market-State Baseline. Transcript corpus QA complete (passed clean or scoped to clean subset). Replay matches live byte-for-byte. Delisted shadow universe ingested and queryable. Trajectory store contains real v5 Contracts. All Phase 1 NEW tests still green.

---

## Next Action

**Two real options, your call:**

1. **Wire the real Baseline to read `headline_observables`** — closes Stone 11e real-data. Connect the toy `MarketStateBaseline` Bayesian Ledger to the new Postgres data. The Baseline reads its narrow 7-series subset at decision time. First end-to-end real-data forecast emerges.
2. **Smoke-test next vendor** — Yahoo for gold + VIX3M + DXY ETF, then decide on MOVE (Polygon/Tradier check) and consensus data (Trading Economics) for the future emissions stone.

**Recommended: (1).** It closes a Phase 2 NEW stone end-to-end and proves the architecture actually consumes real data. Vendor expansion can follow.

### What shipped in the `headline_observables` slice (2026-05-19)

- **Migration** [migrations/versions/7a3c81f4d029_headline_observables.py](migrations/versions/7a3c81f4d029_headline_observables.py) — applied to Neon. Schema: `(series_id, as_of, as_known, value, source, vintage)`, PK `(series_id, as_of, vintage)`, index on `as_of`.
- **Ingest** [src/fingym/data/ingest/fred.py](src/fingym/data/ingest/fred.py) — pulls 32 series via FRED API, idempotent upsert, runs in <1 min, mypy strict clean.
- **Smoke test** [vendor_evaluations/fred_smoke_test.py](vendor_evaluations/fred_smoke_test.py) — confirms coverage / frequency / delay / history depth per series + ALFRED PIT vintage retrieval on revised series.
- **Series in `headline_observables`**: DFF, FEDFUNDS, DGS3MO/2/5/10/30, T10Y2Y, T5YIFR, T10YIE, VIXCLS, DTWEXBGS, DEXUSEU, DEXJPUS, DEXCHUS, DCOILWTICO, DCOILBRENTEU, PCOPPUSDM, CPIAUCSL, CPILFESL, PCEPI, PCEPILFE, PAYEMS, UNRATE, INDPRO, RSAFS, HOUST, GDPC1, ICSA, CCSA, WALCL, M2SL.

**Architectural framing locked**: the `headline_observables` table contains all FRED macro series (continuous time series shape). The Baseline reads its narrow 7-series subset (DFF, DGS10, T10Y2Y, T5YIFR, VIXCLS, DTWEXBGS, DCOILWTICO). The AI Core's macro view of this data comes through the **future emissions table** (richer event records with surprise/consensus/scope), populated from FRED + a consensus vendor when that vendor decision lands. Both readers can access the raw `headline_observables` table; only the Baseline's processed forecast is hidden from the AI Core (per DESIGN.md isolation).

**PIT caveat documented**: revised macro series in `headline_observables` carry current-vintage `as_known`, not first-print. Acceptable for the Baseline's 7-series subset (no material revisions). Full ALFRED vintage tracking deferred to the parked materiality/emissions stone.

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
