# CLAUDE.md

> FinInferenceGym is a contract-scored, point-in-time replay engine for evolving financial belief systems.

## The Goal

We are building a system whose cognitive work is done entirely by AI models — reading raw market evidence, forming forecast distributions over realized returns, proposing signal classes, recommending actions. No hand-coded alpha cognition, no human-engineered features as primary input, no thematic priors taking the place of model reasoning. The verifier IS hand-coded — Bayes, Kelly, proper scoring, point-in-time discipline, empirical per-signal-class reliability via the Forecast Ledger, calibration shrinkage, the margin-of-safety action gate, the structurally isolated Market-State Baseline — that is physics. The verifier is never hand-coded alpha. The model is the engine. Everything below the cognition layer exists to do one thing: verify. Strict math (Bayes, Kelly, proper scoring), strict empirical calibration (per-signal-class reliability tracked over many forecasts; raw forecasts shrunk toward empirical truth before action), strict data discipline (point-in-time, immutable, full provenance), strict promotion (held-out replay only), strict isolation of the Market-State Baseline (the AI never sees its processed forecast; only the same raw observables it consumes). The architecture is shaped so that as frontier models get better, the system gets better automatically; and as verified trajectories accumulate, we eventually train our own model from them that beats the one we started with. Michael is the auditor — his job is to watch for two things: bias creeping in (his preferences, his themes, his trades smuggled in as signal), and any layer losing inspectability. If both stay true, the system rides the exponent without ceiling.

This statement is the synthesis the architecture serves. DESIGN.md is the formal commitments. CLAUDE.md (this file) is the behavior they imply for Claude Code. PYRAMID.md is the running teaching state.

---

The primary AI behavior file for FinInferenceGym. Claude Code reads this at the start of every session.

For project ethos, see [AGENTS.md](AGENTS.md). For architectural commitments, see [DESIGN.md](DESIGN.md). For the build plan, see [BUILD.md](BUILD.md). For engineering decisions, see [TECHNICAL.md](TECHNICAL.md). For current phase, see [PROGRESS.md](PROGRESS.md). For the running teaching state, see [PYRAMID.md](PYRAMID.md).

---

## Source of Truth

- **[DESIGN.md](DESIGN.md)** — architectural constitution. 10 first-principles commitments. Non-negotiable.
- **[TECHNICAL.md](TECHNICAL.md)** — engineering decisions (Python 3.12 / uv, Postgres on Neon, mechanism layer, deployment path).
- **[BUILD.md](BUILD.md)** — 12-week execution plan with teaching, build, design cross-reference, exit criteria, and slippage watches per phase.
- **[PROGRESS.md](PROGRESS.md)** — current phase status, checklist, next action. **Source of truth for "where are we right now."** Updated at the end of every working session.
- **[PYRAMID.md](PYRAMID.md)** — running teaching state. Each conceptual stone of the build is taught here in plain language **before** the code lands. Load alongside PROGRESS.md to see *what's been explained* in addition to *where we are*. Auditability requires it.
- **[memory-design.md](memory-design.md)** — committed memory architecture (four-tier L0-L3 pyramid, promotion gate, git-backed YAML), the deferral list with revisit triggers, and the research evaluated. Source of truth for everything memory-related; expansion of TECHNICAL.md's memory section.
- **[CONTRACT.md](CONTRACT.md)** — MVP spec for the structured terminal output every agent emits (the `Contract` object). Required fields, deferred-field list with triggers, validation rules. Source of truth for the model interface contract; companion to memory-design.md.
- **[FORMULAS.md](FORMULAS.md)** — formal symbols and mathematical notation reference. Grouped by the stone that introduces each. Companion to DEFINITIONS.md (which is prose). Use FORMULAS when you need the exact formula, symbol, or property of a math primitive; use DEFINITIONS for the concept in plain language.
- **[DECISIONS.md](DECISIONS.md)** — log of alternatives proposed and rejected. Do not re-litigate.
- **[BIAS_PATTERNS.md](BIAS_PATTERNS.md)** — specific bias-smuggling patterns to challenge aggressively when they reappear.
- **[AGENTS.md](AGENTS.md)** — minimal pointer file (for non-Claude agents). Just routes to CLAUDE.md.
- **[DEFINITIONS.md](DEFINITIONS.md)** — glossary. Use these terms precisely.
- **[intuitions.md](intuitions.md)** — Michael's running conceptual foundations.
- **[SESSION_START.md](SESSION_START.md)** — first-message protocol for new context windows.

**Authority on conflict**: DESIGN.md > AGENTS.md > BUILD.md / TECHNICAL.md > everything else. DESIGN.md changes only by explicit deliberation. BUILD.md, TECHNICAL.md, and PROGRESS.md update routinely as execution proceeds.

---

## Session Restoration Protocol

When starting a new session (new context window), before producing any non-trivial output:

1. Read **[DESIGN.md](DESIGN.md)** in full. The 10 commitments must be in working memory.
2. Read **[TECHNICAL.md](TECHNICAL.md)** in full. Stack and mechanism layer.
3. Read **[BUILD.md](BUILD.md)** in full. Phase plan and slippage watches.
4. Read **[PROGRESS.md](PROGRESS.md)**. This is the source of truth for current phase.
5. Read **[PYRAMID.md](PYRAMID.md)** in full. This is the running teaching state — what's been explained to Michael in plain language so far, and what the next conceptual stone is. The build cadence is concept-in-PYRAMID-then-code; do not skip ahead.
6. Read **[memory-design.md](memory-design.md)** in full. The committed memory architecture, the deferral list, and the research evaluated. Substantive — do not skip even if the current substep is not memory-specific, because memory decisions constrain agent design upstream.
7. Read **[CONTRACT.md](CONTRACT.md)** in full. The structured terminal output every agent emits. Substantive — agent-design and evaluator-design both depend on the contract spec.
8. Read **[DECISIONS.md](DECISIONS.md)** in full. Rejected alternatives.
9. Read **[BIAS_PATTERNS.md](BIAS_PATTERNS.md)** in full. Named failure modes to challenge.
10. Re-read the slippage watches for the current phase in BUILD.md.

Then summarize back: 10 commitments, current phase + next action, slippage watches, 3 most relevant DECISIONS.md / BIAS_PATTERNS.md entries. Do not propose, plan, or expand scope until Michael confirms the summary is accurate.

Slippage from DESIGN.md is the single biggest project risk during build. Restoring the design state at the start of every session is non-negotiable.

---

## Standing Behavioral Rules

- **Cognition stays in the model. Rigor stays in the system. They do not overlap.** (DESIGN.md #5.) Push constraints to the verification side, never to cognition.
- **The model sees raw evidence.** Never pre-engineer features. (DESIGN.md #6.)
- **Michael is the auditor only.** Never use his discretionary trades as signal, reference, baseline, or "diagnostic." (DESIGN.md #10.)
- **Themes are outputs, not inputs.** Never bake a thematic view into universe selection or hypothesis space.
- **Every "obviously X" is suspect.** Defend it from first principles or flag it as a working assumption.
- **Mechanisms over prompts.** Where a rule can be enforced by code (pre-commit hook, type check, lint, test), it must be. Prose alone is not sufficient. See [mechanisms/](mechanisms/).

---

## Bias-Smuggling Patterns

Twelve specific patterns, with the named examples that occurred during design and the standing response for each, live in [BIAS_PATTERNS.md](BIAS_PATTERNS.md). Read it once at session start. When you see a pattern reappearing, **name it and refuse**.

The patterns: thematic-prior-disguised-as-scope, personal-preference-disguised-as-scope, prestigious-framework-because-prestigious, human-in-the-loop-as-diagnostic, strong-prior-disguised-as-physics, single-model-lock-in, "just for now," narrowing-the-model-interface, buffet-answers, scope-expansion-without-reason, narrative-as-evidence, trade-for-trade's-sake.

---

## Operating Stance

- **Direct, opinionated, willing to push back.** Michael's audit role works only if Claude commits and can be wrong, not lists options to avoid commitment.
- **Execute, don't propose.** When a plan is set, build. Do not re-architect at every turn.
- **Refuse settled questions.** If a proposal matches anything in DECISIONS.md or BIAS_PATTERNS.md, name the entry and decline. Do not re-litigate.
- **Surface real disagreements forcefully once; suppress fake ones.** If Claude has a genuine objection, raise it with reasoning. If overruled, accept and proceed.
- **Buffet answers are a recognized failure mode.** When asked for an opinion, give one. Defend it.

---

## Mechanism Layer

Enforcement of DESIGN.md principles lives in:

- **[mechanisms/](mechanisms/)** — custom pre-commit lints, Claude Code hooks, and import-linter config. See [mechanisms/README.md](mechanisms/README.md) for what each enforces.
- **[.pre-commit-config.yaml](.pre-commit-config.yaml)** — the pre-commit framework configuration.
- **[.claude/settings.json](.claude/settings.json)** — Claude Code hook configuration.

**Mechanisms are protected against quiet relaxation.** The `pre_write_mechanisms.sh` Claude hook requires explicit confirmation for any write inside `mechanisms/`. Any removal or weakening of an enforcement mechanism must be accompanied by a DECISIONS.md entry.

The harness-engineering principle: *enforce quality with mechanisms, not prompts.* Prose fails silently as it goes stale. Failed builds, failed type checks, and broken pointers fail loudly.

---

## Working Rhythm

For each build step, state: what primitive is being learned, why it matters for the final gym, what minimal artifact will be built, what counts as success, what failure would teach.

```text
learn concept
build toy
run experiment
inspect failure
write evaluator
then scale
```
