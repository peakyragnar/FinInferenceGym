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

### Stone 2 — what an outcome is, and where time enters

An **outcome** is the truth, revealed later.

For the coin: after the agent has watched some number of flips and formed a belief, the truth in the box is revealed. The outcome is either `"fair"` or `"biased"` — one of the two hypotheses turns out to be the case.

For a company: after the agent has read a quarter's transcripts and formed a belief about hidden state, time passes. The next-quarter revenue is reported, or the company guides down, or its market share shifts. Those later observations get used as labels. The outcome is what the world reveals at some later moment.

Two characteristics matter:

**(a) The outcome is exactly one hypothesis from the belief's hypothesis set.** Not a probability over hypotheses. Not a "kind of fair." Exactly one of `{fair, biased}` is the truth. (If the truth is "biased but barely," the hypothesis space was wrong — we'd have needed `{very_biased, slightly_biased, fair}`. Stone 4 returns to this.)

**(b) The agent did not see it.** This is the load-bearing point. The belief was formed at time `t_belief`. The outcome is revealed at time `t_outcome > t_belief`. The asymmetry between those two information sets is what makes external evaluation real.

#### Where time enters

Until this stone, we could pretend the agent and the evaluator were operating on the same world at the same time. They are not. They are split by time.

- **Agent's information set:** strictly what is knowable at `t_belief`.
- **Evaluator's information set:** the agent's information PLUS the outcome revealed at `t_outcome`.

The evaluator always knows more than the agent did. The agent can never know what the evaluator knows.

**This asymmetry is the foundation of evaluation.** Without it:

- The agent could trivially get a perfect score by reading the outcome.
- "Evaluation" would mean nothing — anyone who saw the answer key first scores 100%.
- The system could never distinguish a calibrated agent from a confident reward-hacker.

Time is what makes the agent's belief have to be a *belief* and not a *lookup*. It is what makes calibration matter. It is what makes the evaluator load-bearing.

#### What this implies for the engineering

Two principles fall out of the asymmetry immediately:

1. **Point-in-time discipline.** The system has to remember, for every fact, *when it was first knowable.* If a company restated last quarter's revenue today, the agent — when reasoning about a date before that restatement — must see the *original* number, not the restated one. The restated number is a future the agent could not yet see. Showing it would be a time leak. (DESIGN.md #3.)

2. **Time-revealed labels only.** Outcomes are produced by the world later, not by anyone's judgment now. No human-labeled training data. No "Michael says this is the right answer." No narrative scoring. Only what the world reveals at `t_outcome`. (DESIGN.md #10 — Michael as auditor only — is downstream of this.)

#### Worked example — the coin

- `t=0`: belief = `{fair: 0.5, biased: 0.5}`.
- `t=1`..`t=10`: agent observes flips, updates after each. At `t=10` its belief is, say, `{fair: 0.30, biased: 0.70}`.
- `t=later`: the truth in the box is revealed. Outcome = `"biased"`.
- The evaluator scores the `t=10` belief against the `t=later` outcome.

At `t=10`, the agent did not know the outcome. Its 70% confidence in "biased" was inference from the first 10 flips, not lookup. The score grades that inference.

#### Consequences worth noticing now

- **The agent is never graded on luck.** A belief of `{fair: 0.50, biased: 0.50}` on a coin that turned out to be biased got the right side of the call but had no information advantage. We grade the *belief*, not the side.
- **Future emissions are proxies for state, not the state itself.** In finance, no oracle ever announces "the company was actually decaying." We use proxies — next-quarter revenue, future earnings revisions, future market-share trends. Each proxy is itself a hypothesis about how state translates to emission. Stone 4 returns to why this matters.
- **A leak of `t_outcome` info into the agent's `t_belief` info is catastrophic.** The whole project's honesty depends on time discipline. The Postgres schema we built in substep 2 (with `as_of` and `as_known` timestamps per record) is the mechanism that will enforce it once data lands.

The shape of the layer is now visible: belief is what the agent emits at `t_belief`. Outcome is what the world reveals at `t_outcome > t_belief`. The score lives in the gap.

### Stone 3 — what "scoring a belief" means

A **scoring function** is a pure function with this signature:

```
score(belief, outcome) -> number
```

Three pieces.

**(a) It takes two inputs.** The belief (Stone 1) and the outcome (Stone 2). It cannot be a function of just one. A scorer that ignored the belief would just be measuring the outcome — useless, outcomes happen regardless of what the agent thought. A scorer that ignored the outcome would be measuring the belief in isolation — no grounding in reality. Both inputs are required, every time.

**(b) It returns a single number.** Not a verdict ("good" / "bad"). Not a structured object. A single number, because we need to:
- average across many calls to get the agent's overall grade,
- compare two agents head-to-head,
- bucket beliefs by claimed confidence and check observed frequency (calibration curve, Stone 8+ later),
- watch it evolve over time.

All those operations require a single comparable number per `(belief, outcome)` pair.

**(c) Convention in this project: lower is better.** The score is a **loss.** Zero would be perfect; positive is some amount of wrongness. Both Brier and log score follow this convention. ("Higher is better" utility-style scoring also exists and is equivalent up to a sign flip; we stick to loss because it composes more cleanly with averaging and minimization.)

#### Three properties that fall out

- **Deterministic.** Same belief + same outcome → same number, every time. No randomness in the scoring layer.
- **Pure.** No reading external state. No writing external state. No side effects. Pure functions are trivial to test, trivial to compose, trivial to reason about — and the math invariants from DESIGN.md "Architectural Physics" only hold for pure functions.
- **Lives on the verification side.** The scoring function is the verification engine in miniature. **The agent never calls the scorer on its own work.** (DESIGN.md #5, the cognition/verification boundary. The agent proposes; the evaluator disposes.)

#### Concrete shape, on the coin

- belief = `{fair: 0.30, biased: 0.70}`
- outcome = `"biased"`
- `score(belief, outcome)` = some number `s`

That `s` is the bridge between the cognition side (where the agent formed the belief) and the verification side (where reality revealed the outcome and grades the belief against it). Every higher operation in the evaluator is composition over `s` — averaging, bucketing, comparing.

#### What's deliberately unanswered yet

Stone 3 only establishes the *signature.* Three questions remain, each is its own stone:

- **Why grade the belief and not the outcome?** Stone 4. The deepest commitment in the project.
- **What separates a good scoring function from a bad one?** Stone 5. The "proper" property — what makes honesty the dominant strategy.
- **Which specific functions do we use?** Stones 6 and 7 — Brier and log score.

The two scoring functions already in `src/fingym/evaluator/scoring.py` (`brier` and `log_score`) are concrete instances of this signature. Stones 6 and 7 will retroactively teach what those numbers mean and why those two specifically.

### Stones upcoming in this layer

To be taught next, in this order:

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
