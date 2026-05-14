# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2)**

Status: **in progress** — substeps 1–2 complete (engineering scaffolding + Neon database).

See [BUILD.md](BUILD.md#phase-0--evaluator--model-interface-contract--toys-weeks-12) for full phase definition (teaching, build, design cross-reference, exit criterion, slippage watch).

---

## Phase 0 Checklist

| Deliverable | Status |
|---|---|
| Repo skeleton (`src/fingym/` packages, `tests/` tree, `config/`, `memory_registry/`) | ✅ Scaffolded |
| Stub config files (`config/universe.yaml`, `config/vendors.yaml`, `config/agents/baseline.yaml`) | ✅ Scaffolded |
| `README.md` at root | ✅ Present |
| `toys/coin.py` — minimal Bayesian belief-revision toy (at repo root) | ✅ Present (migration to `src/fingym/toys/coin.py` is substep 3) |
| `pyproject.toml` via `uv init`, ruff + mypy strict + pytest configured | ✅ Complete (substep 1) |
| Pre-commit installed and verified | ✅ Complete (substep 1) |
| Neon database connected; `.env` populated; alembic initialized | ✅ Complete (substep 2) |
| `toys/coin.py` migrated to `src/fingym/toys/coin.py` with full type hints | ⬜ Not started (substep 3) |
| Evaluator v0 (scoreboard library: Brier, log score, calibration curve, process-quality flag, decision-quality, capacity-adjusted return) | ⬜ Not started (substep 4) |
| Multi-horizon scoring built into evaluator (1m / 3m / 6m / 1y, plus shorter for toys) | ⬜ Not started (substep 4) |
| Action-space-aware scoring (expression_type tagging: equity-long / -short / option-* / vol-* / pair / no-edge) | ⬜ Not started (substep 4) |
| 3-state synthetic company toy | ⬜ Not started (substep 4) |
| Adversarial test agents (confidently-wrong, always-50%, well-calibrated) | ⬜ Not started (substep 5) |
| Model interface contract (typed I/O — raw evidence in, structured terminal output) | ⬜ Not started (substep 6) |
| Memory artifact schema (versioned, model-readable, horizon-tagged, expression-type-tagged) | ⬜ Not started (substep 7) |
| Property tests smoke subset green | ⬜ Not started (substep 8) |

## Phase 0 Exit Criteria (from BUILD.md)

- Evaluator correctly orders adversarial agents on every scoreboard dimension.
- Reliability diagrams show overconfidence in confidently-wrong agent and zero discrimination in always-50% agent.
- Model interface contract is documented; a stub agent compiles against it.
- Memory schema is documented and validates a sample skill artifact.

---

## Next Action

Next: **substep 3 — migrate `toys/coin.py` into `src/fingym/toys/coin.py` with full type hints under mypy strict.**

Phase 0 Week 1 substeps, in order:

1. **Bootstrap engineering scaffolding.** ✅ `uv init` (Python 3.12 pinned via `.python-version`); `pyproject.toml` configured with all runtime + dev deps and `[tool.ruff]`/`[tool.mypy]`/`[tool.pytest.ini_options]` sections; `uv.lock` committed; `pre-commit install` run via `uv run`; full hook suite green (14 hooks). Claude PostToolUse `ruff format` hook verified to fire on `.py` edits (single-quoted docstring auto-normalized to double). Pre-commit-config bumps: ruff rev v0.6.0 → v0.15.12 (matches venv); mypy hook switched from mirrors-mypy (commented placeholder) to local `uv run mypy` so the type-checker reads the locked dep graph instead of a parallel additional_dependencies list. Scaffolding fixes to make hooks pass: `detect-secrets` pragmas on three template/env-name false positives; RUF002 `×`/`−` → ASCII in two docstrings; `no-discretionary-references` lint caught its own scaffolding's "Michael's transcript corpus" attribution in `src/fingym/data/ingest/__init__.py` — rewritten to "an existing 10-year / 1700-name speaker-tagged corpus" per DESIGN.md #10.
2. **Set up Neon database.** ✅ Neon project "FinInferenceLab" created in `aws-eu-west-2` running Postgres 17.8; pooled connection string stored in local `.env` (gitignored). Psycopg smoke test (`SELECT 1`, `version()`, `current_database()`) returns clean. `uv run alembic init migrations` initialised the migrations tree; `alembic.ini` placeholder `sqlalchemy.url` commented out and the URL injected programmatically from `DATABASE_URL` inside `migrations/env.py` (with `postgresql://` → `postgresql+psycopg://` rewrite so SQLAlchemy dispatches over psycopg3). Empty baseline revision `34760aee56bf_initial.py` generated and applied; `public.alembic_version` row reads `34760aee56bf`. TECHNICAL.md bumped from Postgres 16 to 17 to match what Neon actually provisioned.
3. **Migrate `toys/coin.py`** into `src/fingym/toys/coin.py` with full type hints under mypy strict.
4. **Build the evaluator v0.** Scoreboard library in `src/fingym/evaluator/`: Brier, log score, calibration curve, process-quality flag, decision-quality score. Multi-horizon scoring (1m/3m/6m/1y plus shorter for toys). Action-space-aware tagging.
5. **Build three adversarial test agents** (confidently-wrong, always-50%, well-calibrated) and verify the evaluator distinguishes them on every scoreboard dimension.
6. **Define the model-interface contract** (`src/fingym/agents/interface.py`) as a typed Protocol — raw evidence in, structured terminal output out.
7. **Define the memory artifact schema** (`src/fingym/memory/schema.py`) as a pydantic model; validate a sample artifact in `memory_registry/`.
8. **Run property tests** (smoke subset) to confirm math invariants.

Exit Phase 0 only when all checklist items above are ✅ and adversarial agents are correctly ordered on the scoreboard.

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
