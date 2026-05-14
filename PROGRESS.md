# Progress

Current build status. Updated at the end of every working session.

---

## Current Phase

**Phase 0 — Evaluator + Model Interface Contract + Toys (Weeks 1–2)**

Status: **not started** beyond the initial coin toy.

See [BUILD.md](BUILD.md#phase-0--evaluator--model-interface-contract--toys-weeks-12) for full phase definition (teaching, build, design cross-reference, exit criterion, slippage watch).

---

## Phase 0 Checklist

| Deliverable | Status |
|---|---|
| Repo skeleton (`src/fingym/` packages, `tests/` tree, `config/`, `memory_registry/`) | ✅ Scaffolded |
| Stub config files (`config/universe.yaml`, `config/vendors.yaml`, `config/agents/baseline.yaml`) | ✅ Scaffolded |
| `README.md` at root | ✅ Present |
| `toys/coin.py` — minimal Bayesian belief-revision toy (at repo root) | ✅ Present (migration to `src/fingym/toys/coin.py` is substep 3) |
| `pyproject.toml` via `uv init`, ruff + mypy strict + pytest configured | ⬜ Not started (substep 1) |
| Pre-commit installed and verified | ⬜ Not started (substep 1) |
| Neon database connected; `.env` populated; alembic initialized | ⬜ Not started (substep 2) |
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

Phase 0 Week 1 substeps, in order:

1. **Bootstrap engineering scaffolding.** `uv init`; pin Python 3.12; commit `pyproject.toml`; install pre-commit (`pre-commit install`) so the existing `.pre-commit-config.yaml` is active; verify `.claude/settings.json` PostToolUse hook fires (test by editing a `.py` file and confirming `ruff format` ran).
2. **Set up Neon database.** Create Neon project, store connection string in local `.env`, run a smoke-test connection from Python. Configure alembic. **Do not commit `.env`.**
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
