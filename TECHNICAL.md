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
- `derived_features`
- `beliefs`
- `actions`
- `labels`
- `scores`

Plus operational tables:
- `trajectory` (append-only stream of belief/action/outcome records)
- `vendor_imports` (raw ingest log)
- `promotion_log` (skill promotion / rejection history)

Memory artifacts live as **YAML files in `memory_registry/` in git** — versioned via git for audit history, not in Postgres. This is deliberate: skill provenance and human review benefit from git's diff/blame history.

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
│   ├── beliefs/
│   ├── agents/
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
data/      ←   evaluator/, beliefs/, agents/, cli/        (one-way: data is read by upper layers)
evaluator/ ←   agents/, cli/
beliefs/   ←   agents/, cli/
memory/    ←   agents/, cli/
llm/       ←   agents/, cli/

forbidden:
  data/     →  beliefs/, evaluator/, agents/, llm/, memory/
  evaluator/→  agents/, beliefs/, llm/, memory/
  llm/      →  anything outside src/fingym/llm/
```

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
