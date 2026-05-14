# CLAUDE.md

The primary AI behavior file for FinInferenceGym. Claude Code reads this at the start of every session.

For project ethos, see [AGENTS.md](AGENTS.md). For architectural commitments, see [DESIGN.md](DESIGN.md). For the build plan, see [BUILD.md](BUILD.md). For engineering decisions, see [TECHNICAL.md](TECHNICAL.md). For current phase, see [PROGRESS.md](PROGRESS.md).

---

## Source of Truth

- **[DESIGN.md](DESIGN.md)** — architectural constitution. 10 first-principles commitments. Non-negotiable.
- **[TECHNICAL.md](TECHNICAL.md)** — engineering decisions (Python 3.12 / uv, Postgres on Neon, mechanism layer, deployment path).
- **[BUILD.md](BUILD.md)** — 12-week execution plan with teaching, build, design cross-reference, exit criteria, and slippage watches per phase.
- **[PROGRESS.md](PROGRESS.md)** — current phase status, checklist, next action. **Source of truth for "where are we right now."** Updated at the end of every working session.
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
5. Read **[DECISIONS.md](DECISIONS.md)** in full. Rejected alternatives.
6. Read **[BIAS_PATTERNS.md](BIAS_PATTERNS.md)** in full. Named failure modes to challenge.
7. Re-read the slippage watches for the current phase in BUILD.md.

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

Ten specific patterns, with the named examples that occurred during design and the standing response for each, live in [BIAS_PATTERNS.md](BIAS_PATTERNS.md). Read it once at session start. When you see a pattern reappearing, **name it and refuse**.

The patterns: thematic-prior-disguised-as-scope, personal-preference-disguised-as-scope, prestigious-framework-because-prestigious, human-in-the-loop-as-diagnostic, strong-prior-disguised-as-physics, single-model-lock-in, "just for now," narrowing-the-model-interface, buffet-answers, scope-expansion-without-reason.

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
