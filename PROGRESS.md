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
| `toys/coin.py` — minimal Bayesian belief-revision toy | ✅ Complete |
| 3-state synthetic company toy | ⬜ Not started |
| Evaluator v0 (scoreboard library: Brier, log score, calibration curve, process-quality flag, decision-quality, capacity-adjusted return) | ⬜ Not started |
| Multi-horizon scoring built into evaluator (1m / 3m / 6m / 1y, plus shorter for toys) | ⬜ Not started |
| Action-space-aware scoring (expression_type tagging: equity-long / -short / option-* / vol-* / pair / no-edge) | ⬜ Not started |
| Adversarial test agents (confidently-wrong, always-50%, well-calibrated) | ⬜ Not started |
| Model interface contract (typed I/O — raw evidence in, structured terminal output) | ⬜ Not started |
| Memory artifact schema (versioned, model-readable, horizon-tagged, expression-type-tagged) | ⬜ Not started |

## Phase 0 Exit Criteria (from BUILD.md)

- Evaluator correctly orders adversarial agents on every scoreboard dimension.
- Reliability diagrams show overconfidence in confidently-wrong agent and zero discrimination in always-50% agent.
- Model interface contract is documented; a stub agent compiles against it.
- Memory schema is documented and validates a sample skill artifact.

---

## Next Action

Begin **Phase 0 Week 1**: build the evaluator v0 on the existing coin toy, then extend it to score multi-horizon, action-space-aware outputs. Validate against adversarial test agents.

---

## Update Policy

This file is updated at the **end of every working session**. The update protocol:

1. Mark deliverables ✅ as they complete.
2. Move "Current Phase" forward only when all that phase's exit criteria are met *and* Michael's phase-gate audit has passed (BUILD.md "Phase-Gate Audit").
3. Add a one-line note under "Next Action" so the next session knows where to start.

If a session ends mid-task, "Next Action" should be specific enough that the next session can resume without ambiguity.
