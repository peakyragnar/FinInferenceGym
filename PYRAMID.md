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

A scoring function has signature `score(belief, label) → number`. Both inputs required. Returns a single real number. By convention: **lower is better** (a loss). Zero would be perfect; positive is some amount of wrongness.

Three required properties — each prevents a specific failure mode:

- **Deterministic.** Same belief + same label → same number, every time. A noisy scorer would jitter agent rankings and hide skill below the noise floor; you couldn't tell two analysts apart whose skill gap is below the scorer's noise. The scoring layer must be silent on uncertainty so all observed uncertainty is the agent's.
- **Pure.** No external state read or written. An impure scorer (e.g., one that reads a hidden "regime multiplier") is a vector for silent bias-import: someone can change the dependency and retroactively shift every agent's grade, and the mechanism layer can't catch what's not in the function's source.
- **Lives on the verification side.** The agent never imports or calls the scoring function on its own work (DESIGN.md #5). If it could, it would optimize directly against the metric, silently revise beliefs that would score badly, or — worst case — read the label and emit a perfect belief. Once agents exist, `src/fingym/agents/` will be structurally forbidden from importing `src/fingym/evaluator/` via import-linter.

**Why one number per row.** Every aggregation the evaluator does — mean across calls (agent's grade), bucketing by claimed confidence (calibration curve), per-horizon / per-expression slicing, agent comparisons — requires a single comparable number per `(belief, label)` row.

**Scoreboard reconciliation.** DESIGN.md "scoreboard, not scalar" means *multiple* scoring functions in parallel (Brier + log score + calibration error + decision-quality + ...). Each obeys this Stone 3 signature individually; the scoreboard is the vector across functions per row, then aggregated per column. Diversity across columns is what catches failure modes any single number would miss.

In the code: `brier[H](belief: dict[H, float], outcome: H) -> float` and `log_score[H](belief: dict[H, float], outcome: H) -> float` in `src/fingym/evaluator/scoring.py` are concrete instances of this signature. The parameter is called `outcome` in current code; it carries the `label_value` from a label row. Stones 6 and 7 will explain *why those specific formulas.*

### Stone 4 — why we grade the belief, not the outcome

The choice: grade the whole belief distribution, or grade just "did the agent put the highest probability on the side that won?" These produce **opposite** incentive structures.

**Outcome-grading collapses calibrated and bluffer.** Two agents with the same hit rate (e.g., 7/10) look identical under outcome-grading — the 70/30 calibrated analyst and the always-99/1 bluffer score the same. The math literally discards the distribution information needed to tell skill from confidence.

**Outcome-grading rewards bluffing as the optimal strategy.** Right at 99% scores the same as right at 60%, so the "extra 39% confidence" is free. The agent learns to max-confidence on whichever side it thinks more likely.

**Belief-grading + asymmetric punishment fixes this.** Brier (squaring) and log score punish probability on the wrong side disproportionately. Confidently-wrong costs *much* more than calibrated-wrong. Worked example with both agents at 7/10 hit rate: bluffer averages Brier ≈ 0.59; calibrated 70/30 agent averages ≈ 0.42. They diverge sharply.

**This is THE deepest commitment in the project.** Outcome-grading → guessing system, overconfidence wins. (Proper) belief-grading → learning system, honest calibration wins. Everything downstream — calibration, proper scoring, scoreboard diversity, population search, verified promotion — flows from this choice.

**Why finance defaults to outcome-grading.** Low manager prediction frequency × short evaluation windows × no belief recording infrastructure = too few samples to belief-grade. Our architecture (~1700 names × 4 horizons × continuous belief updates × data-spine recording) sidesteps all three. **Horizon length is NOT the relevant variable** — sample count is. Shorter per-prediction horizons would only accelerate sample accumulation; we'd still belief-grade.

**Steelman.** Outcomes are what compound. Calibration alone is academic; Kelly sizing alone is destructive (oversizes miscalibrated edges). It's calibration + fractional Kelly together that turn inference quality into compound returns. We grade the cause (calibration); compounding turns it into the consequence (log-wealth growth).

### Stone 5 — what makes a scoring rule "proper"

Belief-grading alone isn't enough: some belief-graders still reward bluffing (e.g., linear scoring `S = −belief[outcome]`). The subset of belief-graders that doesn't is called **proper**.

**Proper property.** A scoring rule is proper if, for any true belief `q`, the agent's expected loss is **uniquely minimized by reporting `r = q`**. Honest reporting is the dominant strategy. The rule literally shapes what the agent learns to do.

**Shape difference — visible in a spreadsheet.** Plot expected loss vs reported `r` while holding the true probability `q` fixed:

- **Linear** (improper): straight downhill line. Optimum at the extreme (`r → 1`). Rewards bluffing.
- **Brier** (proper): U-shaped valley with minimum at `r = q`.
- **Log score** (proper): U-shaped valley with minimum at `r = q`, steeper walls at the extremes.

The U-shape exists because Brier and log score punish confident-wrong **disproportionately** to the reward for confident-right. Above `r = q`, the marginal cost of going more extreme outpaces the marginal gain.

**Why the squaring/log shapes specifically:**
- **Brier** = `Σ_h (belief[h] − 1[h==outcome])²`. The square is what asymmetrically punishes confident-wrong vs rewards confident-right.
- **Log score** = `−ln(belief[outcome])`. The log is what makes the punishment grow without bound as the probability on the truth approaches zero.

**Brier vs log score — different shapes of punishment:**
- **Brier**: bounded. Max loss ≈ 2 for binary. Confident-wrong tops out around 1.96 — doesn't explode.
- **Log score**: unbounded. Approaches `+∞` as probability on the truth approaches 0.

**Cromwell and near-Cromwell.** Cromwell's rule: never assign probability exactly 0 to anything not logically certain. Bayesian updating multiplies prior × likelihood; if the prior is 0, the posterior is 0 forever — the hypothesis is unrecoverably ruled out. A **Cromwell failure** is assigning `p = 0` on the truth. A **near-Cromwell failure** is the same shape with very-small-but-nonzero probability (e.g., `p = 0.001`): log score = 6.91; Brier = 1.996. **Log score is the smoke alarm; Brier shrugs.** The Asymmetry of Ruin (intuitions.md #12) makes near-Cromwell structurally dangerous once positions are sized.

**Why both on the scoreboard.** Brier averages politely across many calls (catches general miscalibration). Log score screams at one bad row (catches near-Cromwell). An agent's mean Brier can look fine while one near-Cromwell row pulls the mean log score visibly upward — flagging a hidden disaster the Brier average smoothed over. Running both means catching what either alone would miss.

**Don't combine routinely.** Each scoring function is its own column on the scoreboard. Aggregations happen per column (mean Brier, mean log score, …). Composition into a single number happens **only at explicit decision points with declared rules** (e.g., "promote a memory item if Brier improves AND log score doesn't worsen"). Per DESIGN.md: scoreboard, not scalar. Routine collapse hides failure modes; explicit collapse at a decision point keeps the components visible.

### Stones upcoming in this layer

Both canonical proper scoring rules (Brier, log score) are now conceptually understood AND already implemented in `src/fingym/evaluator/scoring.py` from substep 4a. Remaining stones in Layer 1:

- **Stone 6 — Brier from the formula up.** Algebraic derivation of properness (the valley always lands at `r = q`), explicit link to the implemented code, edge cases.
- **Stone 7 — log score from the formula up.** Same treatment, plus the explicit Cromwell mechanism (`log(0) = −∞` → `−log(0) = +∞`).

Or — given Michael's grasp of the intuition is now solid — skip ahead to **the next layer (the evaluator's math: calibration curves, scoreboard assembly)** and treat Brier/log score's formula derivations as supporting detail to revisit if a failure mode surfaces. Michael's call.

---

## Higher layers — to be taught when we reach them

- **The evaluator's math (Layer 2).** Calibration curve, scoreboard assembly, decision-quality, capacity-adjusted return. Multi-horizon scoring (1m/3m/6m/1y in parallel). Action-space-aware tagging (expression types: equity, options, vol, pairs, no-edge).
- **Evaluator validated on toys (Layer 3).** Coin toy + 3-state synthetic company toy. Adversarial test agents (confidently-wrong, always-50%, well-calibrated). Reliability diagrams. Phase 0 exit criterion: evaluator correctly ranks the three adversarial agents on every scoreboard dimension.
- **Point-in-time data spine + raw-evidence channel (Layer 4).** Six data types (emissions, derived_features, beliefs, actions, labels, scores). Replay/live parity. Delisted shadow universe. Trajectory store in SFT-fit format.
- **Model-driven agent on raw evidence (Layer 5).** Raw evidence in, structured terminal output out. Implied DCF, options-implied probabilities, edge calculator, fractional Kelly sizer.
- **Live operation + memory (Layer 6).** Live calibration dashboard. Memory proposal collection. No Michael comparison.
- **Population + promotion gate (Layer 7).** ≥3 agent variants. Held-out replay, cross-model regression, survivorship check. Domain-of-validity tagging.
- **Year-2 own-model fine-tune (Layer 8).** Cross-model swap. SFT data preparation. The data axis of ride-the-exponent.
