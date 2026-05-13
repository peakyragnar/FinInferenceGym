# CLAUDE.md

This file directs Claude Code. The authoritative project instructions live in [AGENTS.md](AGENTS.md). Read it in full and follow it. This file only highlights what matters most for how Claude should behave.

## Source of Truth

- [AGENTS.md](AGENTS.md) is the operating manual. If anything here conflicts with it, AGENTS.md wins.
- [DEFINITIONS.md](DEFINITIONS.md) is the vocabulary. Use those terms precisely — especially the observation vs. label distinction.
- [intuitions.md](intuitions.md) records the core intuitions Michael is internalizing. Keep it brief; do not let it sprawl.

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
