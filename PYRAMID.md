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

That signature is the whole structure of grading. Stones 1 and 2 gave us the inputs; Stone 3 gives us the function that connects them and produces a comparable verdict. Every higher operation in the evaluator — averaging, bucketing, comparing across agents — is composition over the number this function returns.

#### Reading the signature, piece by piece

**(a) Two inputs are required.** The belief (Stone 1) and the outcome (Stone 2). Not one or the other.
- A scorer that ignored the belief would just be measuring the outcome — useless, outcomes happen regardless of what the agent thought.
- A scorer that ignored the outcome would be measuring the belief in isolation — no grounding in reality.
- Both must enter the function every time. This is what forces the score to be a statement *about the relationship between what the agent thought and what the world revealed.*

**(b) The output is a single number.** Not a verdict ("good" / "bad"). Not a structured object. A single real-valued number. The reason is *not* aesthetic — it's that every aggregation the evaluator needs to do requires a number you can add, sort, average, and compare.

Four concrete aggregations that drive the project:

- **Mean across many calls.** Average score over N predictions → the agent's overall grade.
- **Bucket by claimed confidence.** Group all beliefs where the agent said ~70% and check what fraction were right — this is the calibration curve (taught in Stones 8+). Requires numeric scores per row.
- **Per-horizon and per-expression-type slices.** Same agent might be well-calibrated at 1-month and miserable at 1-year; might be sharp on equity-direction calls and noise on options. Slicing the scores by tag (horizon, expression_type) only works if each row carries a number.
- **Per-agent comparisons.** When the population mechanic kicks in (Phase 4), we compare ≥3 agents on the same scoreboard. Comparison requires a number.

If the score were a structured verdict, none of those reductions would work. Hence: single number.

**(c) Convention in this project: lower is better.** The score is a **loss.** Zero would be perfect; positive is some amount of wrongness. Both Brier and log score follow this convention. "Higher is better" utility-style scoring also exists and is equivalent up to a sign flip; we stick to loss because it composes more cleanly with averaging and minimization, and the "what's my regret over many calls?" framing maps directly onto loss.

#### Three required properties — and why each one matters

The function isn't just `(belief, outcome) → number` for any function. It has to be:

##### Deterministic

Same `belief` + same `outcome` → same number, every time. **No randomness in the scoring layer.**

*Why this matters.* Imagine instead a scoring function that added small random noise: `noisy_brier(b, o) = brier(b, o) + uniform(-0.01, 0.01)`. The consequences:

- The same (belief, outcome) pair would give different numbers on different runs. The agent's grade would jitter.
- Confidence intervals on the agent's grade would be contaminated with scorer noise, not just agent variance.
- You couldn't precisely rank two agents whose true skill gap was below the noise floor — and skill gaps in finance are typically small.

A noisy scorer hides skill behind randomness. The scoring layer has to be silent on uncertainty so that all observed uncertainty is the agent's.

##### Pure

No reading external state, no writing external state, no side effects.

*Why this matters.* Imagine a scoring function that reads a global "current_regime" flag and scales: `regime_aware_brier(b, o) = brier(b, o) * regime_multiplier`. The consequences:

- Same (belief, outcome) gives different scores in different contexts. The same-input-same-output property is gone — and that property is what lets us reproduce, replay, and audit.
- The scoring function now depends on hidden state. You can't reason about an agent's grade without also tracking what regime was active when the scorer ran.
- Worst: someone (a future Claude, a future Michael, an automated process) could silently change the multiplier to "fix" an agent's grade. That's exactly the kind of silent bias-import the project guards against. The mechanism layer can't catch what's not in code; impure functions are how invisible adjustments creep in.

Pure functions are auditable. Impure ones are not.

##### Lives on the verification side — the agent never scores itself

The agent's job is to produce beliefs and actions. The evaluator's job is to take those beliefs, see what the world revealed, and produce a score. **These are two separate code paths, and they must not overlap.** (DESIGN.md #5, the cognition/verification boundary. The agent proposes; the evaluator disposes.)

*Why this matters.* If the agent could read its own scoring function, it could:
- Optimize directly against the score rather than against forming an honest belief — i.e., it could game the metric instead of telling the truth.
- Detect "this belief would score badly" and silently revise it before emitting, claiming it always thought the revised version.
- Worst case: read the outcome that the scoring function uses as input and "predict" it perfectly.

In our codebase, this will eventually be enforced structurally — `src/fingym/agents/` will not be allowed to import from `src/fingym/evaluator/`. The `import-linter` rule that does this is queued in TECHNICAL.md and turns on once the evaluator is more substantial. The principle becomes a structural impossibility, not just a request.

#### Walking through a worked example on the coin

Suppose an agent emits these five beliefs over five sequential evaluations, and the outcome is always `"biased"`. Apply the two scoring functions we already built in substep 4a (`brier` and `log_score` in `src/fingym/evaluator/scoring.py`). Numbers come straight from the smoke check.

| Belief | Outcome | Brier | log_score | Shape |
|---|---|---:|---:|---|
| `{fair: 0.30, biased: 0.70}` | `biased` | 0.1800 | 0.3567 | calibrated, on the right side |
| `{fair: 0.01, biased: 0.99}` | `biased` | 0.0002 | 0.0101 | confident, right |
| `{fair: 0.99, biased: 0.01}` | `biased` | 1.9602 | 4.6052 | confident, wrong |
| `{fair: 0.50, biased: 0.50}` | `biased` | 0.5000 | 0.6931 | wishy-washy |
| `{fair: 1.00, biased: 0.00}` | `biased` | 2.0000 | +∞ | Cromwell violation |

Three things to notice in this table:

1. **Each row is one number per scoring function.** Per row, per function. The signature `(belief, outcome) -> number` is literally what's happening.
2. **Average across the table to get the agent's overall grade.** Mean Brier over the five rows is `(0.18 + 0.0002 + 1.96 + 0.50 + 2.00) / 5 = 0.928`. That single 0.928 is what the agent would be ranked on if we only looked at the mean. The aggregation is just arithmetic over the per-row numbers.
3. **The Cromwell row poisons the log-score mean.** Mean log score across all five rows = +∞ (one infinity makes the mean infinite). This is *correct behavior* per Stone 1's last bullet: probability 0 on the truth is unrecoverable. The evaluator does not get to look the other way. (Stones 7 and 8+ will return to how this enters real reporting — basically, Cromwell violators get flagged, not averaged.)

The same five rows have given us: a number per row, a mean across rows, a flag on one row. That's the whole machinery of the evaluator's most basic operation. Everything else is more elaborate slicing.

#### A note on "scoreboard, not scalar"

DESIGN.md commits to a *scoreboard* — a vector of metrics — not a single scalar. Stone 3's "returns a single number" claim looks like it contradicts that. It doesn't:

- One **scoring function** returns one number per `(belief, outcome)` row.
- A **scoreboard** is what you get by running *multiple* scoring functions (Brier, log score, calibration error, decision-quality, capacity-adjusted return, ...) over the same rows in parallel.
- Per row, the scoreboard is a *vector*: one cell from each function. Across many rows, each column gets aggregated separately.

So: each scoring function obeys the Stone 3 signature individually. The scoreboard is the collection of them. Different scoring functions emphasize different failure modes — Stones 6 and 7 will show how Brier and log score punish overconfidence in different shapes — and that diversity is what makes the scoreboard catch what no single number can.

#### The signature, in the actual code

In `src/fingym/evaluator/scoring.py` from substep 4a:

```python
def brier[H](belief: dict[H, float], outcome: H) -> float:
    ...

def log_score[H](belief: dict[H, float], outcome: H) -> float:
    ...
```

Both functions are literal instances of `score(belief, outcome) -> number`:
- `belief: dict[H, float]` is the probability table from Stone 1, generic over the hypothesis alphabet.
- `outcome: H` is the revealed truth from Stone 2, exactly one hypothesis.
- `-> float` is the single number.

Both functions are pure (only stdlib `math`, no state). Both are deterministic. Neither is imported anywhere by `src/fingym/agents/` (which is empty for now — the boundary will be enforced structurally as soon as agents exist).

#### What's deliberately unanswered yet

Stone 3 only establishes the *signature.* Three questions remain, each is its own stone:

- **Why grade the belief and not the outcome?** Stone 4. The deepest commitment in the project — it's where the project decides to be a learning system rather than a guessing system.
- **What separates a good scoring function from a bad one?** Stone 5. The "proper" property — what makes honesty the dominant strategy.
- **Which specific functions do we use, and how do they implement those properties?** Stones 6 and 7 — Brier and log score, taught from the formulas up.

The functions in `scoring.py` will be retroactively understood after Stones 6 and 7. Right now, you've seen them work numerically; the *why those specific formulas* comes later.

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
