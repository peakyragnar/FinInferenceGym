# The Pyramid

The running teaching index for FinInferenceGym. Each conceptual stone the build rests on has a short distilled summary here — the key concept, the load-bearing properties, and the "watch out for" notes. **Teaching itself happens in chat**, with full examples, counter-examples, and back-and-forth. The summary in this file is written *after* the concept is confirmed, so a future session can rebuild context in a few minutes rather than re-read the whole teaching transcript.

This file is read at session start (per CLAUDE.md). Future sessions pick up the teaching state from here — Michael does not re-teach the foundation each context window.

---

## How this document grows

Cadence per stone:

1. **Teach in chat.** The concept is explained in chat with plain language, concrete numbers, examples, counter-examples. Michael pushes back until it lands.
2. **Summarize here.** Once it lands, this document gets a short, distilled summary — the key concept and load-bearing properties, readable in a minute. Long-form teaching content stays in the chat transcript, not in here.
3. **Code.** The stone is implemented in `src/fingym/`.
4. **Verify.** The implementation runs and matches the worked numbers from the chat teaching.
5. **Next stone.**

This is how auditability is preserved as the build proceeds: every load-bearing piece is something Michael fully understands before it becomes code. The audit role (DESIGN.md #10, BIAS_PATTERNS.md) cannot function if any layer is opaque.

If Claude reverts to "write the full teaching into this file instead of chat" or "build first, summarize after," Michael names it and the cadence resets.

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

**Current position:** atom-of-inference layer. Stones 1, 2, 3 taught.

---

## Layer 1 — The atom of inference

The smallest unit of the entire project. Every higher layer is a variation on the same shape:

> A **belief** is formed about the world. Later, an **outcome** is revealed. The belief is **scored** against the outcome.

Three primitives — belief, outcome, score. From these three, the whole gym grows.

### Stone 1 — what a belief is

A **belief** is a probability distribution over a fixed set of hypotheses: a small table where the rows are the possible worlds, the values are non-negative numbers, and the values sum to exactly 1.

```
Hypothesis  Probability
fair        0.30
biased      0.70
```

That table is the entire data structure the agent emits when forming a belief. Model produces it. Evaluator scores it. Promotion gate compares it. Every other piece of the system reads beliefs in this shape.

Load-bearing properties to remember:

- A belief is never a single guess. "I think it's biased" isn't a belief; `{fair: 0.30, biased: 0.70}` is.
- A belief contains uncertainty by construction. `{0.5, 0.5}` means "no information" — a legitimate belief, not a non-answer.
- Confidence ≠ correctness. A 99% confident belief can be wildly wrong; a 50/50 belief can land on the right side by luck. Scored separately.
- Probability 0 is structurally dangerous: it says "logically impossible," and Bayes cannot recover from it. Returns in Stone 7 (Cromwell).

### Stone 2 — what an outcome is, and where time enters

An **outcome** is the truth, revealed later: exactly one hypothesis from the belief's set, revealed at `t_outcome > t_belief`. The agent does not see it when forming the belief.

The **time asymmetry** between the agent's info (knowable at `t_belief`) and the evaluator's info (the agent's info PLUS the outcome at `t_outcome`) is the foundation of evaluation. Without it, the agent could read the answer key and trivially score 100%; evaluation would mean nothing.

Two engineering principles fall out:

1. **Point-in-time discipline (DESIGN.md #3).** Every fact carries `as_of` and `as_known` timestamps so an agent reasoning about a past date cannot see future revisions. The Postgres schema we set up in substep 2 is the mechanism.
2. **Time-revealed labels only (DESIGN.md #10).** Outcomes come from the world later, never from Michael's judgment, never from narrative. No human-labeled training data.

In finance, future emissions used as proxies for state (next-quarter revenue, future earnings revisions) are themselves hypotheses about how state translates to emission — Stone 4 returns to why this matters.

#### What a label is, practically

An **outcome** is what happens in the world. A **label** is a row in the `labels` table — the recorded, time-stamped piece of data the evaluator uses as the outcome for scoring. The mapping isn't always 1:1.

- **Toy case (coin):** label = outcome. Open the box, see `"biased"`, store the row.
- **Real case (company):** hidden state is never directly observed. The label is **constructed** from future emissions (next-quarter revenue, future guidance, market-share data) via a labelling function we have to design. That function has model assumptions baked in — which proxies, which threshold, which horizon. **Good labels are a real research direction in this project, not a free input.** A wrong labelling function makes the evaluator fake.

Every label row carries: `label_value`, `belief_id` link, `horizon`, `as_known`, `source`, and a `version` for when restatements update the underlying observable.

**One belief → many labels.** A single belief gets scored at multiple horizons in parallel (1m / 3m / 6m / 1y), each with its own labelling-function output and its own `as_known`. The evaluator produces a score per horizon. Discovering at which horizon an agent has edge is empirical, not pre-committed (DESIGN.md "Multi-horizon scoring").

### Stone 3 — what "scoring a belief" means

A scoring function has signature `score(belief, outcome) → number`. Both inputs required. Returns a single real number. By convention: **lower is better** (a loss). Zero would be perfect; positive is some amount of wrongness.

Three required properties:

- **Deterministic.** Same belief + same outcome → same number, every time. A noisy scorer would jitter agent rankings and hide skill below the noise floor.
- **Pure.** No external state read or written. An impure scorer is a vector for silent bias-import that the mechanism layer cannot catch in code.
- **Lives on the verification side.** The agent never imports or calls the scoring function on its own work (DESIGN.md #5). Once agents exist, `src/fingym/agents/` will be structurally forbidden from importing `src/fingym/evaluator/` via import-linter.

**Why one number per row.** Every aggregation the evaluator does — mean across calls (agent's grade), bucketing by claimed confidence (calibration curve), per-horizon / per-expression slicing, agent comparisons — requires a single comparable number per `(belief, outcome)` row.

**Scoreboard reconciliation.** DESIGN.md "scoreboard, not scalar" means *multiple* scoring functions in parallel — each obeys this signature individually; the scoreboard is the vector across functions per row, then aggregated per column.

In the code: `brier(belief, outcome) -> float` and `log_score(belief, outcome) -> float` in `src/fingym/evaluator/scoring.py` are concrete instances of this signature. Stones 6 and 7 will explain *why those specific formulas.*

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
