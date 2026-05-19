# TECHNICAL.md

Engineering decisions and stack choices for FinInferenceGym. This document captures *how we implement* DESIGN.md, not what we implement. Where DESIGN.md is non-negotiable on principles, TECHNICAL.md is the engineering implementation of those principles and may evolve as better tooling emerges.

When TECHNICAL.md conflicts with DESIGN.md, DESIGN.md wins. Routine library upgrades and tooling improvements update this document; architectural changes go through DESIGN.md.

---

## Language and tooling

- **Python 3.12**
- **uv** for dependency management and venv — lock-file based, fast, project-aware.
- **mypy --strict** — enforces the cognition/verification boundary at the type level.
- **ruff** — single tool for linting + formatting. Replaces black + isort + flake8.
- **pytest** + **hypothesis** — property-based tests for math invariants (Bayes, Kelly, scoring rules).
- **pydantic v2** — typed data models and validation at boundaries.
- **structlog** — structured JSON logging for the trajectory store.

## Database

**Postgres 17 hosted on Neon** (free tier, branched workflow).

Rationale:
- Single DB everywhere; production-ready from day 1; cloud-deployable when ready.
- Branched databases for safe experimentation per agent / variant.
- `pgvector` extension covers vector search if/when memory retrieval requires it.
- Portable across Neon / RDS / self-hosted; no vendor lock-in at the code level.

Driver and modeling:
- **psycopg3** as the Postgres driver (async-capable).
- **sqlmodel** for typed ORM (pydantic + sqlalchemy integration).
- **alembic** for migrations. Required for any schema change.

Schema corresponds 1:1 with the six data types from DESIGN.md:
- `emissions`
- `derived_evidence`
- `forecasts`
- `actions`
- `realized_returns`
- `scores`

The `derived_evidence` table is **not created at Phase 0**. The constitutional slot exists (DESIGN.md Layer 0); the table is added in the migration alongside the first concrete derived-evidence artifact (e.g., transcript speaker-turn extraction in Phase 1). The slot exists; the table arrives with a need. Per DESIGN.md, anything labeled "score," "rank," "premium," "factor," "signal," or "quality" is not derived evidence — enforced by `mechanisms/lints/no_alpha_features.py`.

Plus operational tables:
- `trajectory` (append-only stream of forecast/action/realized-return records)
- `vendor_imports` (raw ingest log)
- `promotion_log` (skill promotion / rejection history)
- `headline_observables` (rates, vol, FX, commodities — the Market-State Baseline's input table; also readable by the AI Core)

Plus the **Forecast Ledger view** — a Postgres materialized view `forecast_ledger_reliability` that joins `forecasts` (with `signal_class_id` column) and `realized_returns` (joined on `(name, horizon, expression-type)`), bucketed by claimed probability bucket and signal class, aggregating empirical realized truth-rate over rolling windows. Refreshed nightly or on-demand. Read by the Tradable-Edge Action Engine at decision time for calibration shrinkage. Writes never go to the view directly — only through normal `forecasts` and `realized_returns` table inserts.

Memory artifacts live as **YAML files in `memory_registry/` in git** — versioned via git for audit history, not in Postgres. This is deliberate: skill provenance and human review benefit from git's diff/blame history. The full memory architecture (four-tier L0-L3 pyramid, schema, promotion gate, deferral list, and the research that produced it) is documented in **[memory-design.md](memory-design.md)**. This section gives only the engineering pointers; the architectural decisions live there.

## v5 component modules

Three modules introduced by Constitution v5 (see [DECISIONS.md "Constitution tightening v5"](DECISIONS.md)). All three implemented end-to-end in Phase 1 NEW (closed 2026-05-18): `ledger/` (Cluster A), `action/` (Cluster B), toy `baseline/` (Cluster I). Phase 2 NEW substitutes real-data inputs into the same modules without changing their interfaces.

### Forecast Ledger module — `src/fingym/ledger/`

Maintains the per-signal-class empirical reliability view computed over the `forecasts` and `realized_returns` tables. The Forecast Ledger is the empirical anchor for calibration: it answers "when this agent has historically claimed X% confidence in signal class Y, what fraction of those forecasts realized the claimed bucket?"

- **Reads from**: `forecasts`, `realized_returns` (via `data/`).
- **Writes**: never directly. The view is refreshed from base-table inserts.
- **Read API**: `reliability_for_signal_class(signal_class_id, claimed_bucket) -> empirical_rate`. Called by the Tradable-Edge Action Engine at decision time.
- **Refresh**: scheduled nightly job or on-demand via `refresh_reliability_view()`.
- **Trajectory store role**: the same `forecasts` + `realized_returns` tables that feed the Ledger also serve as the trajectory store for year-2 SFT (DESIGN.md #8). The Ledger is a derived analytical view over the trajectory data.

### Tradable-Edge Action Engine module — `src/fingym/action/`

Converts raw agent forecasts into gated actions via calibration shrinkage + Kelly under cost-aware margin-of-safety threshold.

- **Reads from**: `agents/` (Contract type only — for the raw forecast), `ledger/` (`reliability_for_signal_class`), `data/` (cost / spread / impact models).
- **Writes**: the `action` field of the Contract (or a sibling `calibrated_action` record on the Contract).
- **Pipeline**:
  1. Read raw `F_AI` from Contract.
  2. Read `reliability_for_signal_class` from Ledger for this `signal_class_id`.
  3. Shrink `F_AI` toward empirical reliability → `F_AI_calibrated`.
  4. Compute calibrated expected utility under Kelly using `F_AI_calibrated` and the cost model.
  5. Apply margin-of-safety threshold: if calibrated expected utility clears threshold → emit `TradeAction`; else → `NoAction`.
- **Does NOT** import from `evaluator/` (the gate is forward-acting; scoring is a separate concern).

### Market-State Baseline module — `src/fingym/baseline/`

Structurally isolated control. Produces forecast distributions over realized returns using only headline observable inputs. The AI Core never sees the Baseline's processed forecast; the audit layer uses it to compute incremental AI edge attribution columns.

- **Reads from**: `data/` — exclusively the `headline_observables` table (rates, vol, FX, commodities). No other inputs.
- **Writes**: rows in `forecasts` table tagged `agent_id = 'baseline'` (or a sibling table; final schema decided when the module ships).
- **Isolation**: `src/fingym/agents/` cannot import from `src/fingym/baseline/`. Enforced by `import-linter` rule (added below). The AI Core consumes the same `headline_observables` table raw, but never imports the Baseline's processed forecast.
- **Attribution**: the evaluator computes `incremental_AI_edge = AI realized edge − Baseline realized edge` per `(name, horizon, expression-type)` from the rows both produce. This is an audit column, not an action input.
- **Input set is load-bearing**: rates, vol, FX, commodities. Broadening this set blurs the attribution layer; see BUILD.md Phase 2 NEW slippage watch "Baseline observable creep."

## Model interface contract

The structured terminal output that every agent emits is the `Contract` object spec'd in **[CONTRACT.md](CONTRACT.md)**. The pydantic model lives in `src/fingym/agents/contract.py` (Phase 0 substep 6 deliverable). The validator (`src/fingym/agents/contract_validator.py`) enforces the required-field constraints listed in CONTRACT.md "Validation."

A model output that does not land in a valid `Contract` is rejected at the verifier gate, not scored, and recorded as a verifier-rejection in the operational log. This is the code-level enforcement of DESIGN.md #5 (cognition / verification boundary) at the agent boundary.

The trajectory store (per DESIGN.md #8) writes one row per `Contract` with full provenance and the `cognitive_audit_trail` field preserved. The trail captures (initial forecast, additional reasoning iterations, updated forecast, action change) per cognitive step, which the Phase 4 VOI mechanism reads to compute "did more thinking change the action?" Capturing the trail is a Phase 0 design requirement; the VOI mechanism that consumes it is Phase 4.

## LLM swap layer

`src/fingym/llm/` wraps all model providers behind a typed model-interface contract (DESIGN.md #7):

- `contract.py` — Protocol class defining input/output shape (raw evidence in, structured terminal output out).
- `anthropic.py`, `openai.py`, `google.py` — concrete implementations.
- `openweights.py` — Phase 5+.

Code outside `src/fingym/llm/` never imports `anthropic` / `openai` / `google-genai` directly. Enforced by `mechanisms/lints/no_hardcoded_models.py` at pre-commit time.

## Data ingest

- **norgate-data** SDK (Python) — PIT fundamentals + prices, **including delisted names** (non-negotiable for survivorship mitigation).
- **ib_insync** — IBKR live feed for prices + options.
- **Custom transcript ingest** — Michael's existing 10-year / 1700-name corpus, normalized to the canonical six-data-type schema.
- **fredapi** — free macro data (rates, yields, inflation).

All ingest writes through the schema with versioned timestamps (`as_of`, `as_known`, `source`, `version`, and `corpus_bias` flag where applicable).

## Repo structure

```
FinInferenceGym/
├── pyproject.toml             # uv, ruff, mypy, pytest config
├── uv.lock
├── .env.example               # template; .env gitignored
├── .pre-commit-config.yaml    # pre-commit hooks
├── .claude/settings.json      # Claude Code hooks
├── alembic.ini                # migrations config
├── importlinter.toml          # architectural import boundaries
│
├── DESIGN.md, BUILD.md, PROGRESS.md, DECISIONS.md, CLAUDE.md, AGENTS.md,
├── DEFINITIONS.md, intuitions.md, SESSION_START.md, BIAS_PATTERNS.md,
├── TECHNICAL.md, README.md
│
├── config/                    # YAML configs (universe, vendors, agents)
│
├── migrations/                # alembic migrations
│
├── mechanisms/                # enforcement layer (harness-engineering)
│   ├── README.md
│   ├── lints/                 # custom pre-commit lints
│   └── hooks/                 # Claude Code hooks
│
├── src/fingym/                # main package (src-layout)
│   ├── toys/
│   ├── evaluator/
│   ├── data/
│   ├── memory/
│   ├── agents/
│   ├── ledger/                # v5 — Forecast Ledger (Phase 1 NEW)
│   ├── action/                # v5 — Tradable-Edge Action Engine (Phase 1 NEW)
│   ├── baseline/              # v5 — Market-State Baseline; isolated from agents/ (Phase 1 NEW toy; Phase 2 NEW real)
│   ├── llm/
│   └── cli/
│
├── tests/
│   ├── unit/
│   ├── property/              # hypothesis-based
│   └── integration/
│
├── memory_registry/           # YAML in git
├── trajectory_store/          # gitignored
└── data_cache/                # gitignored
```

## Mechanism layer

Per the harness-engineering principle: **enforce quality with mechanisms, not prompts.** Documented prose fails silently; failed builds and broken pointers fail loudly.

### Pre-commit hooks

| Hook | Enforces |
|---|---|
| `mypy --strict` | Type discipline; cognition/verification boundary at code level |
| `ruff check` + `ruff format` | Lint + format |
| `detect-secrets` | No API keys or connection strings in commits |
| `check-added-large-files` | No accidental trajectory/data commits |
| `check-yaml` / `check-json` / `check-toml` | Config file syntax |
| `import-linter` | Architectural import boundaries |
| `no-discretionary-references` (custom) | DESIGN.md #10 — no Michael/discretionary references in production code |
| `no-hardcoded-models` (custom) | DESIGN.md #7 — no direct LLM SDK imports outside llm/ |
| `pydantic-schema-validate` (custom) | All pydantic models validate sample fixtures |
| `memory-artifact-validate` (custom) | memory_registry/ YAML files validate against schema |
| `alembic-migration-check` (custom) | Schema changes require matching migration |
| `property-tests-smoke` | Math invariants don't regress |
| `progress-md-warn` (custom, warning only) | Reminds to update PROGRESS.md |

### Claude Code hooks

| Hook | Event | Action |
|---|---|---|
| `pre-write-design-protected` | PreToolUse: Edit/Write | Require explicit confirmation for writes to DESIGN.md, DECISIONS.md, AGENTS.md |
| `pre-write-mechanisms` | PreToolUse: Edit/Write | Require explicit confirmation for writes to mechanisms/ |
| `post-write-format` | PostToolUse: Edit/Write | Auto-run `ruff format` on .py files |
| `post-write-mypy` | PostToolUse: Edit/Write | Auto-run `mypy` on changed .py files |
| `pre-bash-destructive` | PreToolUse: Bash | Surface destructive commands (rm -rf, DROP TABLE, force-push) for confirmation |
| `post-tool-progress-nudge` | PostToolUse | Remind to update PROGRESS.md if phase deliverables changed |

### Pytest gates

- Property-based tests for Bayesian update commutativity, Kelly monotonicity, Brier properness.
- Coverage gate: `evaluator/` ≥95%, `beliefs/` ≥90%.
- Adversarial-agent regression: evaluator must always correctly order confidently-wrong / always-50% / well-calibrated.
- Replay-vs-live parity: byte-identical output for sample as-of dates.
- Promotion-gate-as-code: sample memory items must pass/fail the gate as specified.

### Architectural import boundaries (import-linter)

```
# Allowed imports (one-way: data is read by upper layers; the v5 gate flows agents → action → ledger; baseline runs in parallel)

data/      ←   evaluator/, agents/, ledger/, action/, baseline/, cli/
agents/    ←   action/, cli/                                       (action consumes the Contract type)
ledger/    ←   action/, evaluator/, cli/                           (action calls reliability_for_signal_class; evaluator reads for diagnostics)
memory/    ←   agents/, cli/
llm/       ←   agents/, cli/

# Forbidden (load-bearing isolation rules)

  agents/    →   evaluator/, action/, ledger/, baseline/    (cognition cannot reach the verifier, the gate, the calibration ledger, or the baseline — DESIGN.md #5 + #2)
  baseline/  →   agents/, evaluator/, action/, ledger/, memory/, llm/   (the Baseline is isolated; reads ONLY data/.headline_observables — DESIGN.md #2)
  evaluator/ →   agents/, action/, llm/, memory/
  data/      →   evaluator/, agents/, ledger/, action/, baseline/, llm/, memory/
  llm/       →   anything outside src/fingym/llm/
```

The `agents/ ↛ baseline/` and `baseline/ ↛ agents/` rules are the load-bearing v5 isolation: the AI Core consumes the same raw `headline_observables` the Baseline consumes, but it never sees the Baseline's processed forecast.

## Operator Configuration and Observability

Per DESIGN.md "Operator Configuration and Observability" — the architecture commits to operator visibility into every decision and tunability over operational parameters (vs locked architectural commitments). This section spells out the implementation.

### Configuration file layout

Operational parameters live in `config/` as versioned YAML. Every change is a git commit with full audit trail.

```
config/
├── cost_models/
│   ├── equity_large_cap.yaml         # spread, impact k, ADV thresholds, alpha-decay parameters
│   ├── equity_microcap.yaml
│   ├── options.yaml
│   └── pair.yaml
├── action_engine/
│   ├── margin_of_safety_weights.yaml # composition: cost + uncertainty + miscalibration + capacity slack
│   ├── shrinkage_priors.yaml         # prior_strength per asset class / signal class
│   └── action_gates.yaml             # minimum sample sizes for gate to clear
├── ledger/
│   └── refresh_cadence.yaml          # how often the Forecast Ledger reliability view refreshes
├── promotion_gate/
│   ├── thresholds.yaml               # held-out improvement minimums, cross-model regression criteria
│   └── retire_criteria.yaml          # when promoted L3 skills get demoted back to L2 or retired
├── emissions/
│   └── materiality_thresholds.yaml   # per category: macro/rates (default 25 bps), CPI surprise (0.2%), commodities (5% daily), FX (3% DXY), credit (25 bps HY), per-sector tuning
└── kill_switches.yaml                # per-name, per-signal-class, per-agent stop flags (manual operator override)
```

Each YAML file has a schema validated by a pre-commit hook. The schema enforces that tunable parameters fall within sensible ranges (e.g., `prior_strength > 0`; `minimum_sample_size >= 5`).

### Dashboard endpoints

The dashboard presentation layer reads from the data substrate (scoreboard, Forecast Ledger view, promotion log, Postgres tables) and renders four views:

| View | What it shows |
|---|---|
| `dashboard/decisions` | Live + historical decisions, organized by name / signal class / agent / horizon. Per decision: forecast, calibrated forecast, EU, margin-of-safety breakdown (all components), tradable edge score, final action. "Why did this happen" drill-down per decision. |
| `dashboard/ledger` | Per-signal-class reliability tables with sample sizes. Rolling-window calibration drift indicators. Drill-down: which forecasts contribute to each cell. |
| `dashboard/promotions` | Skills currently in L2 probationary. Promotion checks passed / failed per skill. Historical promotions, rejections, demotions, retirements. |
| `dashboard/cost_accuracy` | Per-product type: estimated vs realized costs (from Stone 14's `realized_edge - nominal_edge` decomposition). Drift detection — cost-model parameters might need recalibration. |

Implementation stack TBD when Phase 3 lands; likely FastAPI + a minimal React/Streamlit frontend, served from the same Fly.io/Railway deployment.

### Kill switches

Operator override of the Action Engine, with audit log:

```python
# Per-name kill switch
kill_switches.add_name("AAPL", reason="material non-public event suspected", actor="michael")

# Per-signal-class kill switch
kill_switches.add_signal_class("commodity_supply_shock", reason="regime mismatch detected", actor="michael")

# Per-agent kill switch
kill_switches.disable_agent("bayes_v1", reason="needs retraining after model upgrade", actor="michael")
```

Each kill switch action records: timestamp, actor, scope, reason, effective-from / effective-until timestamps. Recorded in Postgres `kill_switch_log` table (append-only).

The Action Engine checks `kill_switches` before emitting a `TradeAction` — if any matching kill switch is active, the action is overridden to `NoAction` with `reason="operator_kill_switch"` on the Contract. The override IS recorded on the Contract for audit; the agent's `recommended_action` is preserved separately so the audit shows what would have happened without the override.

### Mechanism enforcement

| Mechanism | What it enforces |
|---|---|
| Pre-commit `config-schema-validate` (custom, queued for Phase 1 NEW Cluster B) | All YAML in `config/` validates against its schema |
| Pre-commit `no-locked-params-in-config` (custom, queued for Phase 1 NEW Cluster B) | Architectural-locked parameters (e.g., the shrinkage formula structure) never appear in `config/` — prevents accidental relaxation of an architectural commitment |
| Git commits in `config/` | Audit trail for every operational parameter change |
| Postgres `kill_switch_log` table | Audit trail for every kill switch invocation |
| Code-level: `agents/` cannot import from `config/` (only verifier-side modules can) | Cognition is not parameterized by operator settings — keeps cognition / verification boundary clean |

### Phase progression

| Phase | What lands |
|---|---|
| Phase 1 NEW Cluster B | The Action Engine reads cost-model config from `config/cost_models/` and margin-of-safety weights from `config/action_engine/`. Tunable parameters live in YAML from day 1. |
| Phase 1 NEW Cluster G | Promotion gate reads thresholds from `config/promotion_gate/`. |
| Phase 2 NEW | Real cost-model calibration begins; cost-model config files start receiving updates based on observed execution data. |
| Phase 3 (live deployment) | Dashboard endpoints + kill switches deployed alongside live operation. Backend live; frontend optional but recommended. |
| Phase 4 | Promotion-gate dashboard activates as memory artifacts are evaluated against real held-out data. |
| Phase 5 | Cost-model accuracy dashboard refined with full year-2 retail capacity-adjusted data. |

### What the architecture commits to (and what it doesn't)

**Commits to:**
- Every operational parameter is in a versioned config file.
- Every config change is a git commit (audit trail).
- Every decision is recorded with full provenance in the Contract.
- The operator can override (kill switches) with an audit log.
- The architecture distinguishes locked (can't change in operation) from tunable (operator changes via config).

**Does not commit to:**
- A specific dashboard framework (React, Streamlit, Grafana — any of these would work; chosen in Phase 3)
- A specific deployment topology for the dashboard (could be co-located with the API or separate)
- Real-time vs batched dashboard refresh — tunable per view based on what makes sense

The architecture is about the contract between operator, system, and audit trail. The implementation details (UI framework, exact endpoints, refresh cadence) are operational choices that can evolve.

---

## Deployment path

### Year 1 (local development)
- Code runs on Michael's Mac.
- Database on Neon free tier (cloud).
- LLM API calls to Anthropic / OpenAI / Google (cloud).
- Trajectory store: Postgres tables + local logs.
- No 24/7 operation; agent runs are manual.

### Year 1.5 (when 24/7 operation is desired)
- Deploy Python code to Fly.io or Railway (cheap VM).
- Same Neon connection string. No code changes.
- Agent runs continuously.

### Year 2+ (open-weights / own model)
- Modal or RunPod for GPU rentals (model swap test, eventual SFT).
- Or local GPU.
- Fine-tuned own-model deployed as a population member alongside frontier API agents.

## CI/CD

- **GitHub Actions** runs the full pre-commit suite + pytest on every PR.
- Block merge if any check fails.
- No automatic deployment; production deploys are manual.

## What this document does not cover

- Architecture and principles → [DESIGN.md](DESIGN.md)
- 12-week build plan → [BUILD.md](BUILD.md)
- Current phase status → [PROGRESS.md](PROGRESS.md)
- Rejected design alternatives → [DECISIONS.md](DECISIONS.md)
- AI behavior → [CLAUDE.md](CLAUDE.md)
- Bias-smuggling patterns to challenge → [BIAS_PATTERNS.md](BIAS_PATTERNS.md)
- Vocabulary → [DEFINITIONS.md](DEFINITIONS.md)
- Intuitions → [intuitions.md](intuitions.md)

## Change control

Routine library upgrades, version bumps, and additions to the mechanisms layer update TECHNICAL.md directly. Major engineering changes (database swap, language change, removal of an enforcement mechanism) require explicit deliberation and a corresponding DECISIONS.md entry.
