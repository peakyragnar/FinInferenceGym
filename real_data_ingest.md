# Real-Data Ingest Plan

> **Source of truth for what data lands in our Postgres, from which vendor, at which tier, in which stage.** Companion to [BUILD.md Phase 2](BUILD.md) (which sequences the architectural work) and [TECHNICAL.md](TECHNICAL.md) (which fixes the engineering stack). This document fixes the **data scope** by stage.

This file is read when starting any data-ingest-related work and updated when stages complete.

---

## Purpose

Phase 2 NEW substitutes real data into the toy-trained architecture, one data type at a time. The architecture is proven (Phase 1 NEW closed 2026-05-18). What remains is connecting it to the real world.

This document specifies:
1. The **stages** of real-data ingest, in execution order
2. The **data** ingested in each stage (vendor, endpoint, table, schema shape)
3. The **gating criteria** between stages (when do we advance)
4. The **rejected paths** so future sessions don't relitigate

---

## Anchor commitments

All ingest serves these architectural commitments. Any ingest decision that violates one of these is wrong by construction.

- **DESIGN.md #2**: Forecast distribution over realized returns, calibrated empirically. We need realized returns (prices) and the evidence inputs that drive forecasts (fundamentals, filings, transcripts, macro).
- **DESIGN.md #3**: Time one-way valve. Every row carries `as_of` (reference date) + `as_known` (when it became knowable to the market). Replay at decision time `t` must see only `as_known ≤ t`.
- **DESIGN.md #5**: Cognition / verification boundary. The data spine delivers raw evidence; nothing in the ingest layer scores, ranks, or interprets — that's the model's job.
- **DESIGN.md #6**: Raw evidence native reasoning. The model sees raw values, raw filings, raw transcripts. No pre-engineered features at ingest. (Pre-computed indicators like RSI/MACD are explicitly NOT ingested.)
- **DESIGN.md #8**: Two-axis improvement. Every ingested row preserved with full provenance — the trajectory store is fit for year-2 own-model SFT.
- **Operational Constraints**: Universe broad by default. Multi-horizon scoring. No paper trading.
- **DESIGN.md #10**: Michael as auditor only. No discretionary judgment encoded in ingest decisions.

---

## Architectural principles

Locked decisions about HOW we ingest, regardless of stage.

### 1. Long-table schema for time-series + structured data

One row per (entity, period, attribute) tuple. Adding new attributes or sources doesn't require schema migration. Matches the canonical six-data-type pattern in DESIGN.md Layer 0.

Concrete pattern (used by every ingest table):

```
(entity_id, as_of, as_known, value, source, vintage)
PRIMARY KEY (entity_id, as_of, ..., vintage)
```

`vintage` defaults to 1 for first-print / current-vintage data. Restatement rows append with higher vintage numbers.

### 2. PIT discipline preserved per row

Every row carries:
- `as_of` — the date the data refers to (e.g., trading day for a price; quarter end for a filing)
- `as_known` — when the data became known (publish timestamp; SEC filing date; vendor ingest timestamp)

A query at decision time `t` must filter to `as_known ≤ t`. The `time_leak_guard` mechanism enforces this; ingest just records the timestamps honestly.

### 3. Replay-vs-live parity through lag-adjusted `as_known`

For vendor-delivered data that lags the underlying event (Massive's ~1-3 week filing-to-API latency), the historical replay uses `as_known = filing_date + median_observed_lag`. The lag is measured empirically during Stage 2 (Advanced subscription gives us a sample). Replay then matches the latency live operation will experience. See [BUILD.md Phase 2 Stone 25](BUILD.md).

### 4. Observation-only architecture

The system learns from `forecast → realized return → score`. No trades are required for the learning loop. Forecasts get graded by the market continuously. Execution (manual or via broker API) is a separate Phase 3+ operator decision. Sizing parameters use defaults until execution begins; refinement is downstream.

### 5. Vendor for parsing, never reinvent

Parsing SEC XBRL to normalized fundamentals is a vendor job (Massive). The historical attempt to build this in-house consumed ~1 month with too many edge cases to be reliable. We pay vendors for normalization and accept their freshness. Direct SEC EDGAR usage is limited to the **submissions feed** (low-effort, structured filing-event detection at hours latency).

### 6. Structured-data-first

Stages 1 and 2 ingest structured (numeric / tabular / event-shaped) data. Unstructured text (10-K body, 8-K body, news article bodies, transcript NLP) is deferred to Stage 4 (or never). The AI Core has plenty of evidence to work with from structured + Michael's existing transcript corpus.

### 7. No pre-engineered features

Massive endpoints for pre-computed technical indicators (RSI, MACD, SMA, EMA) are **not ingested**. The model is given raw evidence per DESIGN.md #6. If it wants moving averages, it computes them itself.

---

## Universe

The set of names for which we ingest equity data.

| Tier | Composition | Size | Purpose |
|---|---|---|---|
| **Production analytical universe** | Michael's existing transcript corpus (~1700 names, all currently listed) + delisted-during-window cousins identified via Massive's `/v3/reference/tickers?active=false` filtered to delisted-in-window | ~2000 tickers | The set we ingest prices, fundamentals, news, etc. for. |
| **Active capital universe** | Subset of production analytical where (eventually) calibrated edge × capacity × Kelly justifies action | Emergent | Not relevant until execution begins. |
| **Learning / toy universe** | 30 toy companies in `synthetic_market.py` | 30 | Architecture validation only. Frozen at Phase 1 NEW close. |

Universe selection is by **operational and structural criteria only** — coverage of evidence (we have transcripts for these names), survivorship-completeness (delisted-during-window included). Never by sector, theme, market cap preference, or any DESIGN.md-rejected criterion.

The universe is searchable per DESIGN.md ("Searchable vs Architectural" table). Expansion to broader names later is a config change, not an architectural one.

---

## Stages

Each stage is a discrete, validated unit. We complete one and validate before starting the next.

### Stage 0 — Macro substrate (FRED) ✅ COMPLETE (2026-05-19, commit `5db188e`)

**What landed**: 202,672 rows across 32 FRED time series on the `headline_observables` table. Free vendor, ALFRED PIT first-print discipline verified.

**Tables**:
- `headline_observables` — daily/weekly/monthly/quarterly time series

**Series ingested** (full list):

| Category | FRED series |
|---|---|
| Policy rate | `DFF`, `FEDFUNDS` |
| Treasury curve | `DGS3MO`, `DGS2`, `DGS5`, `DGS10`, `DGS30`, `T10Y2Y` |
| Inflation expectations | `T5YIFR`, `T10YIE` |
| Volatility | `VIXCLS` |
| FX | `DTWEXBGS`, `DEXUSEU`, `DEXJPUS`, `DEXCHUS` |
| Commodities | `DCOILWTICO`, `DCOILBRENTEU`, `PCOPPUSDM` |
| Macro emissions — monthly | `CPIAUCSL`, `CPILFESL`, `PCEPI`, `PCEPILFE`, `PAYEMS`, `UNRATE`, `INDPRO`, `RSAFS`, `HOUST` |
| Macro emissions — quarterly | `GDPC1` |
| Macro emissions — weekly | `ICSA`, `CCSA` |
| Other | `WALCL`, `M2SL` |

**Code**:
- Migration: [migrations/versions/7a3c81f4d029_headline_observables.py](migrations/versions/7a3c81f4d029_headline_observables.py)
- Ingest: [src/fingym/data/ingest/fred.py](src/fingym/data/ingest/fred.py)
- Smoke test: [vendor_evaluations/fred_smoke_test.py](vendor_evaluations/fred_smoke_test.py)

**Cost**: $0 ongoing. FRED is free.

**Status**: Live in Postgres. PIT-discipline verified via ALFRED on CPIAUCSL (April 2020 first-print 255.902 vs current 256.032) and PAYEMS (131,072 vs 130,426). The macro substrate is operational.

---

### Stage 1 — Equity structured data on Massive Developer ⬜ NEXT

**Purpose**: Wire the architecture to real equity data without committing to the Advanced subscription. Prove ingest → schema → wire-up → Baseline → AI Core works on what Developer tier already gives us.

**Vendor**: Massive Developer tier (~$79/mo, already subscribed).

**Universe**: Production analytical universe (~2000 tickers).

**Time depth**: Maximum available per series. Developer tier permits 10-year history for OHLCV. Other endpoints inherit the same depth. No artificial alignment — different series with different earliest dates is fine (DESIGN.md PIT handles this naturally).

**Tables created in Stage 1**:

| Table | Granularity | Source endpoint |
|---|---|---|
| `equity_prices` | One row per (ticker, trading_date, vintage) | `/v2/aggs/ticker/{T}/range/1/day/...` |
| `corporate_actions_splits` | One row per (ticker, ex_date, split_event) | `/v3/reference/splits` |
| `corporate_actions_dividends` | One row per (ticker, ex_date, cash_dividend_event) | `/v3/reference/dividends` |
| `tickers` | One row per (ticker, snapshot_date) — reference metadata including `delisted_utc` | `/v3/reference/tickers` (active + `active=false` for delisted) |
| `fundamentals` | One row per (ticker, period_of_report, fiscal_period, statement_type, line_item, vintage) | `/vX/reference/financials` (legacy combined endpoint — works on Developer, verified) |
| `news_metadata` | One row per (article_id) — headline + ticker + sentiment metadata, NOT full body text | `/v2/reference/news` |
| `ipos` (optional) | One row per IPO event | `/v3/reference/ipos` (since 2008) |

**Schema sketch for `fundamentals`** (the most complex):

```sql
CREATE TABLE fundamentals (
    ticker             TEXT NOT NULL,
    period_of_report   DATE NOT NULL,
    fiscal_year        TEXT NOT NULL,
    fiscal_period      TEXT NOT NULL,        -- 'Q1' / 'Q2' / 'Q3' / 'Q4' / 'FY' / 'TTM'
    timeframe          TEXT NOT NULL,        -- 'quarterly' / 'annual' / 'ttm'
    filing_date        DATE,
    statement_type     TEXT NOT NULL,        -- 'balance_sheet' / 'income_statement' / 'cash_flow_statement' / 'comprehensive_income' / 'ratios'
    line_item          TEXT NOT NULL,        -- canonical name from Massive
    value              NUMERIC,
    unit               TEXT,
    label              TEXT,
    item_order         INTEGER,
    source             TEXT NOT NULL,        -- 'massive_legacy' or 'massive_per_statement'
    vintage            INTEGER NOT NULL DEFAULT 1,
    ingested_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, period_of_report, fiscal_period, statement_type, line_item, vintage)
);
```

Long-table format. Step 2 (Advanced per-statement endpoints) populates the SAME table with additional rows under `source = 'massive_per_statement'` and richer line items. No schema change required.

**What's deliberately NOT in Stage 1** (gated to Stage 2):
- Form 4 (insider transactions)
- 13-F (institutional holdings)
- Short interest, short volume
- Float
- Per-statement fundamentals endpoints (richer than legacy combined)
- Risk factors / risk categories (machine-readable)
- 10-K / 8-K text extracts
- Benzinga (analyst, consensus, guidance, earnings)

**Storage estimate**: ~250–500 MB total. Fits Neon free tier (0.5 GB) — no upgrade needed at this stage.

**Engineering effort**: ~2 days. One alembic migration creating 6–7 tables, one ingest module per logical group following the FRED pattern, SQL validation queries, spot-checks against Massive's website.

**Gating criteria to advance to Stage 2**:

| Criterion | What proves it |
|---|---|
| Schema is stable | All Stage 1 tables created, populated, queryable. No revision needed. |
| Wire-up validated | Real Baseline (Stone 11e real-data) reads `headline_observables` + `equity_prices` and produces forecasts on at least one company. Real AI Core (Stone 28) reads `fundamentals` + `equity_prices` + `news_metadata` (+ transcripts from existing corpus) and produces forecasts. |
| Replay end-to-end works | Historical replay produces calibrated Contracts with realized-return scoring for ≥1 company over ≥1 year. |
| Promotion gate fires on real evidence | At least one memory proposal lands at L2 or L3 via real held-out replay calibration (not the toy mode). |

Only after these criteria are met do we move to Stage 2.

---

### Stage 2 — Massive Advanced bulk download + Benzinga (1-month subscription burst) ⬜ LATER

**Purpose**: Backfill the rich data Developer tier doesn't expose, in a one-month Advanced burst, then downgrade. Per-statement fundamentals (richer), Form 4, 13-F, short interest, machine-readable risk factors, SEC filings index, plus Benzinga's analyst + consensus + guidance + earnings data.

**Vendor**:
- Massive Advanced (~$199/mo, 1 month) — bulk historical download
- Benzinga add-on (~$300/mo, verify in account; possibly 1 month bulk + lower tier ongoing)

**Universe**: Same as Stage 1.

**Time depth**: Maximum available on each endpoint. Advanced unlocks all-history (back to 2003-09-10 system limit for prices; XBRL fundamentals back to ~2009; Form 4 back to 2003; 13-F back to 1999).

**Tables added or extended in Stage 2**:

| Table | Granularity | Source endpoint |
|---|---|---|
| `fundamentals` (extended) | Additional rows under `source='massive_per_statement'` with richer line items per statement | `/vX/reference/financials/balance-sheets` + `/income-statements` + `/cash-flow-statements` + `/ratios` |
| `insider_transactions` | One row per Form 4 transaction | `/vX/reference/sec/form-4` |
| `institutional_holdings` | One row per (filer, ticker, quarter) | `/vX/reference/sec/13-f` |
| `short_interest` | One row per (ticker, settlement_date) | `/vX/reference/short-interest` |
| `short_volume` | One row per (ticker, trading_date) | `/v2/reference/short-volume` |
| `float` | One row per (ticker, snapshot_date) | `/vX/reference/financials/float` |
| `risk_factors_structured` | One row per (ticker, filing, risk_category) — machine-readable risk extracts, NOT full 10-K body | `/vX/reference/sec/risk-factors` + `/risk-categories` |
| `sec_filings_index` | One row per filing — pointers to filings on EDGAR | `/vX/reference/sec/filings` |
| `analyst_ratings` | One row per rating event | `/vX/reference/partners/benzinga/analyst-insights` + `/analyst-ratings` |
| `corporate_guidance` | One row per guidance issuance | `/vX/reference/partners/benzinga/corporate-guidance` |
| `earnings_estimates` | One row per (ticker, period, estimate_source) | `/vX/reference/partners/benzinga/earnings` |

Plus optional (decide at Stage 2 start):
- `consensus_ratings` — aggregated analyst ratings from Benzinga
- `corporate_events` — Wall Street Horizon forward-looking calendar (~separate partner if available on Advanced)

**What stays NOT in Stage 2** (deferred indefinitely):
- 10-K / 8-K full body text (Michael's call: structured first; unstructured later)
- News article bodies (only metadata + sentiment)
- Real-time / WebSocket / tick data
- Options chains
- Futures
- Forex / Crypto

**Storage estimate**: ~10–15 GB. Requires Neon Pro upgrade (~$19/mo).

**Engineering effort**: ~3 days. Add ~10 new tables and ingest modules. Most follow the Stage 1 patterns.

**The downgrade plan**: After bulk download completes, downgrade Massive to Developer + Benzinga to its lower ongoing tier. Steady-state ~$180–280/mo.

**Cost summary**:
- Month 1 burst: ~$500 (Massive Advanced + Benzinga) one-time
- Month 2+ steady: ~$180–280/mo (Developer + Benzinga lower) + $19 Neon Pro = ~$200–300/mo

---

### Stage 3 — Ongoing data refresh ⬜ STEADY-STATE

**Purpose**: Keep data current after the Stage 2 historical bulk download.

**What runs daily/weekly/quarterly**:

| Data | Source post-downgrade | Cadence |
|---|---|---|
| Daily OHLCV | Massive Developer `/v2/aggs/...` | Daily |
| Splits + dividends | Massive Developer | Daily polling |
| New ticker registrations + delistings | Massive Developer `/v3/reference/tickers` | Daily |
| Fundamentals updates (new quarterly filings) | Massive Developer `/vX/reference/financials` (legacy combined endpoint — empirically fresh within 1-3 weeks of SEC filing) | Daily polling |
| News + sentiment | Massive Developer | Daily polling |
| FRED macro updates | FRED API | Daily polling |
| Analyst ratings + earnings + guidance | Benzinga lower tier | Real-time / daily polling |
| Filing event timestamps (low-latency) | **SEC EDGAR submissions feed** (free, ~hours latency) | Daily polling |

**SEC EDGAR submissions feed** is a small addition — captures the EVENT of a filing (ticker, form type, filing date, accession number) within hours of SEC publication. Does NOT include parsing of the filing content — that comes from Massive 1-3 weeks later. This bridges the freshness gap for filing-event-driven emissions.

**Engineering effort**: ~1 day to build the submissions feed reader. Other ongoing ingest is just running the Stage 1+2 modules on a schedule.

---

### Stage 4 — Unstructured text ⛔ DEFERRED INDEFINITELY

**Status**: Explicitly deferred by Michael. Structured data first; text last.

**What's deferred**:
- 10-K Sections (Business + Risk Factors body text)
- 8-K text (parsed item content body)
- News article bodies
- Transcript NLP / management commentary extraction
- Press release bodies

**Why deferred**:
- AI Core has plenty of structured evidence from Stages 1–3 to validate the architecture
- Text extraction adds significant complexity (chunking, embedding strategy, prompt token budget)
- Best done after structured architecture is proven and we know what specific patterns the AI is searching for
- Existing transcript corpus is available raw for use whenever we decide to wire it in

**Revisit trigger**: when (a) the architecture has been proven on structured data, (b) we have specific hypotheses about what narrative patterns the AI should search, (c) we're ready to engineer the token-budget / chunking question.

---

## Rejected paths (do not relitigate)

### SEC EDGAR XBRL direct ingest for fundamentals

**Considered**: Build our own SEC EDGAR XBRL → normalized fundamentals pipeline as a free alternative to paying Massive for fundamentals parsing.

**Rejected because**: Michael spent ~1 month attempting this previously. Too many edge cases (heterogeneous XBRL taxonomies, company-specific extensions, restatement / amendment linking, period semantics, currency / unit conversion, footnote interpretation) to be reliable. Time-value of engineering attention is better spent on alpha generation, not data plumbing the vendor handles. Pay the vendor.

**Limited exception**: SEC EDGAR submissions feed for filing EVENT timestamps (Stage 3). This is NOT parsing — it's just reading the "what was filed today" feed. Simple, structured, reliable. Distinct from XBRL parsing.

### Paper trading (simulated portfolios with fake P&L)

**Considered**: Standard "paper trade for N months before going live."

**Rejected because**: DESIGN.md "No paper trading." Michael is already trading live with discretion; the system doesn't need to ramp into real money. The system grades itself on realized returns regardless of whether trades are executed. Observation-only mode produces real calibration evidence; simulation produces nothing useful that the observation loop doesn't already provide.

### Real-time / tick-level data ingest

**Considered**: Subscribe to Massive's real-time tier and WebSocket streams for tick-level trades + quotes.

**Rejected because**: We're not market-making or HFT. Daily close + multi-day forecasts don't need sub-second data. Tick data adds TB-scale storage with no architectural payoff. Future revisit if/when intraday strategies become relevant — not before.

### Options / Futures / Forex / Crypto in Phase 2 NEW

**Considered**: Subscribe to Massive Options Advanced + Futures Advanced for the full equity-complex coverage per DESIGN.md.

**Rejected because**:
- **Options**: deferred to Phase 3+. The architecture supports the full equity-complex action space; we don't need options DATA until the AI Core is expressing options trades.
- **Futures**: substantially overlapping with FRED's commodity coverage. The one real gap (Treasury futures for MOVE proxy) can be approximated with realized vol of FRED's daily Treasury yields. Not worth $249/mo.
- **Forex / Crypto**: out of scope per DESIGN.md "Structural exclusions" (US equity focus).

### Pre-computed technical indicators (RSI, MACD, SMA, EMA from Massive)

**Considered**: Ingest Massive's pre-computed technical indicator endpoints.

**Rejected because**: DESIGN.md #6 — no pre-engineered features as primary input. The model computes indicators itself from raw price data if it wants them. Ingesting them would smuggle vendor-encoded interpretations into the cognition layer.

### ETF Global, Fable Data, Economy (Massive native macro)

**Considered**: Massive's partner data on ETF flows, European consumer spending, Massive-native macro endpoints.

**Rejected because**:
- ETF Global: lower architectural priority for v1; defer
- Fable Data: European consumer spending, not US-relevant
- Economy: redundant with FRED (which is canonical)

---

## Operator-tunable parameters established by ingest

Per DESIGN.md "Operator Configuration and Observability," these parameters are operator-tunable (versioned in `config/`, audit-logged) — locked architectural commitments use other parameters.

| Parameter | What it controls | Stage |
|---|---|---|
| **Universe ticker list** | Which companies' data we ingest | Stage 1+ |
| **Time depth per series** | How far back to pull (Massive plan-tier limits this; we set per-series targets within) | Stage 1+ |
| **Ingest poll cadence** | How often each endpoint is polled in steady state | Stage 3 |
| **Vendor lag estimate for `as_known` adjustment** | Median lag between SEC filing and Massive populating (empirically measured during Stage 2) | Stage 2 onward |
| **Bucket cutpoints per `headline_observable` series** | Numeric thresholds for the Bayesian Ledger's macro state buckets (e.g., VIX <15 vs ≥15) | Wired in Stage 1 |
| **Cost-model defaults** (spread, impact coefficient, commission, alpha decay) | Per-asset-class assumptions used until execution provides real fills | Wired in Stage 1; refines in execution-mode |
| **Sizing scale factor** (operator multiplier on fractional Kelly) | Defaults to 0 in observation-only; >0 when execution starts | Execution-mode |

Architecturally-locked parameters (not in `config/`, only changeable via DECISIONS.md deliberation):
- Long-table schema structure
- Six-data-type canonical schema
- PIT discipline rules
- The `headline_observables` membership envelope (rates / vol / FX / commodities only)

---

## Cost summary

| Phase | One-time | Ongoing |
|---|---|---|
| Stage 0 (FRED) | $0 | $0 |
| Stage 1 (Massive Developer + transcript corpus already owned) | $0 (using existing subscription) | $79 (current Massive Developer subscription) |
| Stage 2 (Massive Advanced 1-month + Benzinga) | ~$500 (1-month burst) | — |
| Stage 3 (ongoing, post-downgrade) | — | $180–280/mo (Massive Developer + Benzinga lower tier) + $19 Neon Pro = ~$200–300/mo |

**Year-1 total operating budget for data: ~$2,500–$4,000.**

Compare to: typical hedge-fund analyst SaaS spend is $20k–100k/year per seat. We're operating at retail-scale data spend by being deliberate about scope.

---

## Status snapshot (updated as stages complete)

| Stage | Status | Commit |
|---|---|---|
| Stage 0 — FRED | ✅ Complete (2026-05-19) | `5db188e` |
| Stage 1 — Massive Developer | ⬜ Next | — |
| Stage 2 — Massive Advanced bulk + Benzinga | ⬜ Gated on Stage 1 | — |
| Stage 3 — Ongoing refresh | ⬜ Steady state after Stage 2 | — |
| Stage 4 — Unstructured text | ⛔ Deferred | — |

---

## Change control

This document is updated when:

1. **A stage completes** — mark status ✅, link the commit, note what landed
2. **A vendor decision changes** — document the new vendor + revised stages
3. **The universe scope changes** — document the new scope + reasoning
4. **A rejected path needs to be revisited** — add to the "Rejected paths" section the new evidence that warrants revisiting

This document does NOT change when:
- Implementation bugs are fixed (code change, not architecture)
- Routine parameter tuning happens (config commit, not architecture)
- A new line item / FRED series gets added within an existing stage's scope (extending the per-stage list is fine)

Substantive changes follow the same protocol that protects DESIGN.md and BUILD.md.
