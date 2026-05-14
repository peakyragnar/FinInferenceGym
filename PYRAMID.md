# The Pyramid

The running teaching state of FinInferenceGym. Each conceptual stone the build rests on is taught here, in plain language, **before** the code that implements it lands. As the build progresses, this document accumulates.

This file is read at session start (per CLAUDE.md). Future sessions pick up the teaching state from here — Michael does not re-teach the foundation each context window.

---

## How this document grows

Cadence per stone:

1. **Concept.** The stone is explained here, in plain language, using the simplest available fixture (usually the coin toy) with concrete numbers. Michael reads it. Pushes back if anything is unclear.
2. **Code.** Only after the concept is grounded, the stone is implemented in `src/fingym/`.
3. **Verify.** The fixture runs against the implementation; the numbers match the worked example above.
4. **Next stone.** Only then do we move up.

This is how auditability is preserved as the build proceeds: every load-bearing piece is something Michael fully understands before it becomes code. The audit role (DESIGN.md #10, BIAS_PATTERNS.md) cannot function if any layer is opaque.

If Claude reverts to "build first, summarize after," Michael names it and the cadence resets.

---

## The pyramid

The system is built up in layers. Each layer rests on the one below. A wrong layer poisons everything above it.

```
                                          [Year-2 own-model fine-tune]
                                  [Population of agents + promotion gate]
                                       [Live operation + memory]
                                  [Model-driven agent on raw evidence]
                          [Point-in-time data spine + raw-evidence channel]
                      [Evaluator validated on toys w/ adversarial agents]
                    [The evaluator's math: scoring rules + calibration]
                  [The atom of inference: belief, outcome, score]   ← currently teaching
            [INFRASTRUCTURE: uv, mypy, pre-commit, Neon, alembic]   ← built (Phase 0 substeps 1–2)
```

**Infrastructure** (below the pyramid line) is not part of the project itself — it is the ground the pyramid stands on. Tooling gate (mypy strict, ruff, custom design lints, pre-commit), data substrate (Postgres 17 on Neon, alembic migrations), and the mechanism layer that enforces DESIGN.md at the code level. Built in Phase 0 substeps 1–2.

**Current position:** at the start of the atom-of-inference layer. Stone 1 has been taught.

---

## Layer 1 — The atom of inference

The smallest unit of the entire project. Every higher layer is a variation on the same shape:

> A **belief** is formed about the world. Later, an **outcome** is revealed. The belief is **scored** against the outcome.

Three primitives — belief, outcome, score. From these three, the whole gym grows.

### Stone 1 — what a belief is

In ordinary English, a "belief" is just a thought. "I believe the coin is biased." That's not what we mean here.

In this system, a **belief** is a **probability distribution over a set of hypotheses.** That's three pieces.

**(a) A set of hypotheses.** First you have to declare what the possible worlds are. For the coin, the set is just `{fair, biased}` — two possible worlds. For a company, it could be `{strengthening, stable, decaying}` — three. For a chess position, it could be `{white wins, black wins, draw}` — three. The set is fixed up front. You cannot add hypotheses mid-game.

**(b) A probability over each hypothesis.** For each possible world, the belief assigns a number between 0 and 1. "I think there's a 70% chance the coin is biased" means: probability 0.70 assigned to the hypothesis `"biased"`.

**(c) The numbers sum to exactly 1.** This is what makes it a *distribution*. The hypotheses are exhaustive — one of them is true — so the probabilities have to cover the full 100%. A belief of `{fair: 0.70, biased: 0.30}` is valid. A belief of `{fair: 0.70, biased: 0.40}` is not — it sums to 1.10, which would mean there's more than 100% certainty somewhere, which is nonsense.

So a belief looks like a small table:

| Hypothesis | Probability |
|---|---|
| fair   | 0.30 |
| biased | 0.70 |

That single table — an exhaustive set of possible worlds with a non-negative number on each that sums to 1 — is **the entire data structure** the agent emits when forming a belief. The model produces beliefs. The evaluator scores beliefs. The promotion gate compares beliefs. Every other piece of the system reads beliefs in this shape.

A few consequences worth noticing now, because they'll matter later:

- **A belief is never a single guess.** "I think it's biased" is not a belief in our sense. "I'm 70% biased, 30% fair" is.
- **A belief contains uncertainty by construction.** The agent that says `{fair: 0.50, biased: 0.50}` is reporting "I have no idea." That's a legitimate belief, not a non-answer.
- **A belief can be confident.** `{fair: 0.01, biased: 0.99}` says "I'm nearly certain it's biased."
- **Confidence is not the same as correctness.** A belief of `{fair: 0.01, biased: 0.99}` can be wildly wrong (if the coin is fair) or near-perfect (if it's biased). We don't know until the outcome is revealed. Confidence and correctness are scored separately — Stone 2 onward.
- **Probability 0 is structurally dangerous.** Assigning 0 to a hypothesis means "this is logically impossible," and Bayes cannot recover from that — no future evidence can resurrect a hypothesis you've ruled out. Stone 7 (Cromwell's rule) returns to this.

That table is the foundation. Everything else in the project is built on top of it.

### Stones upcoming in this layer

To be taught next, in this order:

- **Stone 2 — what an outcome is.** And the critical fact that the agent never sees it at the moment it forms the belief. Time enters the picture here.
- **Stone 3 — what "scoring a belief" means.** A function that takes a belief and an outcome and returns a number.
- **Stone 4 — why we score the belief, not the outcome.** The single most important conceptual move in the project. The difference between a learning system and a guessing system.
- **Stone 5 — what makes a scoring rule "proper."** The mathematical property that means honesty is the dominant strategy.
- **Stone 6 — the Brier score.** First canonical proper scoring rule.
- **Stone 7 — the log score, and Cromwell's rule.** Second canonical proper scoring rule, and why `log_score = +∞` is a feature, not a bug.

---

## Higher layers — to be taught when we reach them

- **The evaluator's math (Layer 2).** Calibration curve, scoreboard assembly, decision-quality, capacity-adjusted return. Multi-horizon scoring (1m/3m/6m/1y in parallel). Action-space-aware tagging (expression types: equity, options, vol, pairs, no-edge).
- **Evaluator validated on toys (Layer 3).** Coin toy + 3-state synthetic company toy. Adversarial test agents (confidently-wrong, always-50%, well-calibrated). Reliability diagrams. Phase 0 exit criterion: evaluator correctly ranks the three adversarial agents on every scoreboard dimension.
- **Point-in-time data spine + raw-evidence channel (Layer 4).** Six data types (emissions, derived_features, beliefs, actions, labels, scores). Replay/live parity. Delisted shadow universe. Trajectory store in SFT-fit format.
- **Model-driven agent on raw evidence (Layer 5).** Raw evidence in, structured terminal output out. Implied DCF, options-implied probabilities, edge calculator, fractional Kelly sizer.
- **Live operation + memory (Layer 6).** Live calibration dashboard. Memory proposal collection. No Michael comparison.
- **Population + promotion gate (Layer 7).** ≥3 agent variants. Held-out replay, cross-model regression, survivorship check. Domain-of-validity tagging.
- **Year-2 own-model fine-tune (Layer 8).** Cross-model swap. SFT data preparation. The data axis of ride-the-exponent.
