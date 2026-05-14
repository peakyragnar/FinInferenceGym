# AGENTS.md

Michael owns this project.

This file is the **project operating manual** — the ethos under which all design and build work proceeds. It is intentionally short. It does **not** restate the architecture, the build plan, or the rejected alternatives — those live in dedicated files and are authoritative there.

---

## Document hierarchy

Read these in the order given. Authority on conflict flows top-down.

1. **[DESIGN.md](DESIGN.md)** — Architectural constitution. The 10 first-principles commitments. Non-negotiable on architecture. Changes only by explicit deliberation.
2. **[CLAUDE.md](CLAUDE.md)** — The primary AI behavior file for this project. Session restoration protocol, standing behavioral rules, common bias-smuggling patterns, operating stance. Claude reads this at the start of every session. If you're building with Claude, this is the operative AI guide.
3. **[BUILD.md](BUILD.md)** — Operational 12-week execution plan. Phases, teaching, build deliverables, design cross-reference, exit criteria, slippage watches.
4. **[PROGRESS.md](PROGRESS.md)** — Current phase status, checklist, next action. Source of truth for *where are we right now.*
5. **[DECISIONS.md](DECISIONS.md)** — Alternatives proposed and rejected during design, with rationale. Read to avoid re-litigating settled questions.
6. **[DEFINITIONS.md](DEFINITIONS.md)** — Glossary. Use these terms precisely.
7. **[intuitions.md](intuitions.md)** — Michael's running conceptual foundations.
8. **[SESSION_START.md](SESSION_START.md)** — First-message protocol for new context windows.

**For all build and architectural questions, the answer lives in DESIGN.md, BUILD.md, PROGRESS.md, or DECISIONS.md — not here.**

---

## Core Goal

Build an AI-native Financial Inference Gym that absorbs frontier AI improvements to generate calibrated, verifiable alpha in equity markets through hidden-state inference, market-implied belief recovery, and rigorous evaluator-driven self-improvement.

Optimized for **absolute compound growth** (log-wealth), not Sharpe.

Full architecture: [DESIGN.md](DESIGN.md). Operational plan: [BUILD.md](BUILD.md).

---

## Teaching-First Mandate

This project is a curriculum, not a monolithic system. Michael must be able to audit every layer; that requires understanding every layer; that requires teaching-first construction.

For every component:

1. Explain the intuition in simple, concrete terms.
2. Build the smallest working version.
3. Run or inspect the result.
4. Explain what the result teaches.
5. Only then move to the next layer.

If Michael does not yet understand the intuition behind a layer, stop and teach that layer before building above it.

Michael's role is the **auditor of the auditing system** (DESIGN.md #10), not the analyst. The teaching-first mandate exists so the auditor remains capable.

---

## Working Rhythm

For each build step, state:

- What primitive is being learned.
- Why that primitive matters for the final gym.
- What minimal artifact will be built.
- What would count as success.
- What failure would teach.

```text
learn concept
build toy
run experiment
inspect failure
write evaluator
then scale
```

---

## Process Non-Negotiables

This is a summary. The full architectural set is in [DESIGN.md](DESIGN.md) "First-Principles Commitments." The full execution set is in [BUILD.md](BUILD.md). The full set of bias-smuggling patterns to challenge is in [CLAUDE.md](CLAUDE.md).

- **Evaluator before agent.** Calibration before deployment.
- **Verified updates only.** Skills, features, hypothesis spaces survive held-out replay or they don't persist.
- **Cognition stays in the model; rigor stays in the system; they do not overlap.** Constraints migrate to the verification side, never sit on cognition.
- **The model sees raw evidence.** No pre-engineered features as primary input. No templated reasoning. No fixed ontologies.
- **No bias-import.** Themes are outputs, not inputs. Michael is the auditor only, never a training signal, baseline, or reference for system calibration.
- **Two-axis improvement.** Model swap (frontier or open-weights) AND data axis (verified trajectories → year-2 own-model fine-tune). Both architectural, designed in from day 1.
- **Population, not single agent.** Multiple agents varying in (model × memory × prompt × reasoning), competing on the evaluator scoreboard.
- **No paper trading, no Sharpe optimization, no narrative scoring, no closed-box end-to-end systems, no insider information, no HFT** (structural exclusions per DESIGN.md, not preferences).

For rejected frameworks and bias patterns: [DECISIONS.md](DECISIONS.md).

---

## A note on this file's history

Earlier versions of AGENTS.md contained a "15-layer build pyramid" and an "Immediate First Primitive" section that predated DESIGN.md. Those have been superseded. The architectural layers now live in DESIGN.md ("The Six Layers"); the build sequence lives in BUILD.md ("Phase 0–5"). If you encounter the old pyramid or first-primitive section anywhere, it is stale — use the current sources above.
