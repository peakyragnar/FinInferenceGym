# CLAUDE.md

This file directs Claude Code. The authoritative project instructions live in [AGENTS.md](AGENTS.md). Read it in full and follow it. This file only highlights what matters most for how Claude should behave.

## Source of Truth

- [DESIGN.md](DESIGN.md) is the architectural constitution. Principles here are non-negotiable. If anything else conflicts with DESIGN.md, DESIGN.md wins.
- [BUILD.md](BUILD.md) is the practical 12-week execution plan derived from DESIGN.md. Each phase has teaching, build, design cross-reference, exit criterion, and slippage-watch components.
- [AGENTS.md](AGENTS.md) is the operating manual (how to work on the project).
- [DEFINITIONS.md](DEFINITIONS.md) is the vocabulary. Use those terms precisely — especially the observation vs. label distinction.
- [intuitions.md](intuitions.md) records the core intuitions Michael is internalizing. Keep it brief; do not let it sprawl.

Order of authority on conflict: **DESIGN.md > AGENTS.md > BUILD.md > everything else.** DESIGN.md changes only by explicit deliberation; BUILD.md updates as we execute.

## Session Restoration Protocol

When starting a new session (new context window) on this project, do the following before producing any non-trivial output:

1. **Read [DESIGN.md](DESIGN.md) in full.** Every principle. Don't skim. The 10 first-principles commitments must be in working memory before any build work proceeds.
2. **Read [BUILD.md](BUILD.md) in full.** Phase plan, design cross-reference, slippage watches.
3. **Identify the current phase.** Check git log, recent files in `toys/`, any `PROGRESS.md` if present. Confirm with Michael if unclear.
4. **Re-read the slippage watches for the current phase.** These are the specific things most likely to drift.

Slippage from DESIGN.md is the single biggest project risk during build. Restoring the design state at the start of every session is non-negotiable.

## Standing Behavioral Rules

- **Cognition stays in the model. Rigor stays in the system. They do not overlap.** (DESIGN.md #5.) When in doubt, push constraints to the verification side, not the cognition side.
- **The model sees raw evidence.** Never pre-engineer features for it. (DESIGN.md #6.)
- **Michael is the auditor only.** Never use his discretionary trades as a signal, reference, baseline, or "diagnostic." (DESIGN.md #10.)
- **Themes are outputs, not inputs.** Never bake a thematic view (e.g., "AI dispersion") into universe selection or hypothesis space.
- **Every "obviously X" is suspect.** Defend it from first principles or flag it as a working assumption.

## Core Goal (from AGENTS.md)

Build an AI-native Financial Inference Gym: an evaluator-centered system where agents, feature extractors, source diets, valuation rules, and bet structures are tested against hard point-in-time financial outcomes. Not a faster Wall Street. A new kind of evaluator.

## Teaching-First Mandate

This project is a curriculum, not a monolith. For every component:

1. Explain the intuition in simple, concrete terms.
2. Build the smallest working version.
3. Run or inspect the result.
4. Explain what the result teaches.
5. Only then move to the next layer.

If Michael does not yet understand the intuition behind a layer, stop and teach that layer before building above it.

## Build Order

Build the pyramid bottom-up. Do not start a layer until the ones below it are understood and working:

1. Evaluator discipline
2. Hidden-state inference
3. Costly observation and source selection
4. Bandits and contextual bandits
5. Toy POMDP environment
6. Gymnasium environment interface
7. Deterministic valuation / DCF mechanics
8. Monte Carlo valuation distributions
9. Point-in-time historical replay
10. Transcript parsing and feature extraction
11. Source-diet tournaments
12. Market-implied belief inversion
13. AlphaEvolve-style artifact search
14. RL information-acquisition policy
15. Full historical Financial Inference Gym

Current focus: the **first primitive** — a tiny hidden-company-state environment teaching hidden state, noisy observations, costly information, belief formation, trade/no-trade decisions, reward design, and reproducible evaluation.

## Non-Negotiables

- Do not build the full gym first.
- Do not skip foundational toy systems.
- Do not add data complexity before the evaluator exists.
- Do not add RL before the environment and reward function are clear.
- Do not add AlphaEvolve-style search before there is a hard evaluator.
- Do not pull in options, news, social, or large universes early.
- Do not optimize for impressive demos. Optimize for intuition, correctness, falsifiability.
- Do not treat synthetic environments as truth — they are teaching tools.
- Do not treat profitable backtests as sufficient — calibration, reasoning quality, costs, and out-of-sample survival matter.

## Working Rhythm

For each step, state: what primitive is being learned, why it matters for the final gym, what minimal artifact will be built, what counts as success, what failure would teach.

```text
learn concept
build toy
run experiment
inspect failure
write evaluator
then scale
```

## Style

- Small, explicit steps. Teach before building above a layer.
- Keep new docs short and operational. Prefer extending existing files (`intuitions.md`, `DEFINITIONS.md`) over creating new ones.
- Use the vocabulary from `DEFINITIONS.md` consistently. Never blur observation and label.
