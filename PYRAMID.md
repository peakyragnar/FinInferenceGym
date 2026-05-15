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
                    [The evaluator's math: scoring rules + calibration]   ← starting next
                  [The atom of inference: belief, outcome, score]   ← Stones 1–7 taught
            [INFRASTRUCTURE: uv, mypy, pre-commit, Neon, alembic]   ← built (Phase 0 substeps 1–2)
```

**Infrastructure** (below the pyramid line) is not part of the project itself — it is the ground the pyramid stands on. Tooling gate (mypy strict, ruff, custom design lints, pre-commit), data substrate (Postgres 17 on Neon, alembic migrations), and the mechanism layer that enforces DESIGN.md at the code level. Built in Phase 0 substeps 1–2.

**Current position:** Layer 1 (atom of inference) complete — Stones 1 through 7 taught and committed; both canonical proper scoring rules (Brier, log score) implemented in `src/fingym/evaluator/scoring.py`. Ready to start Layer 2 (the evaluator's math).

---

## Table of contents — the full pyramid

The complete plan, by layer. Stones taught and committed are marked **✅**; stones below the current frontier are **⬜** and tentative — exact ordering, grouping, and count may evolve as we build. BUILD.md phases are noted in parentheses for cross-reference.

### Foundation: INFRASTRUCTURE ✅ (Phase 0, substeps 1–3)
- Tooling gate: uv, pyproject, mypy strict, ruff, custom design lints, pre-commit
- Data substrate: Neon Postgres 17, alembic baseline
- First toy in src layout: `toys/coin.py` → `src/fingym/toys/coin.py` under mypy strict

### Layer 1 — The atom of inference ✅ (Phase 0, substep 4a)
- Stone 1 ✅ — what a belief is
- Stone 2 ✅ — what an outcome is, and where time enters (with: what a label is, practically)
- Stone 3 ✅ — what "scoring a belief" means
- Stone 4 ✅ — why we grade the belief, not the outcome
- Stone 5 ✅ — what makes a scoring rule "proper"
- Stone 6 ✅ — the Brier score, formula and properties
- Stone 7 ✅ — the log score, formula and Cromwell
- Stone 7a ✅ — **the four-thing decomposition** (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`). Bridge from Layer 1 to Layer 2: Layer 1 scored a belief vs reality; Layer 2 scores a belief vs a *competing belief* (the market's), arbitrated by reality. Anchor: money lives in `P_AI − P_market` only when an `Action(A)` monetizes it after costs *and* `S_true` validates the side. Runnable toy: `uv run python -m fingym.toys.four_thing_decomp` ([src/fingym/toys/four_thing_decomp.py](src/fingym/toys/four_thing_decomp.py)). Symbols in [FORMULAS.md](FORMULAS.md). Full distilled summary in Layer 1 body below.

### Layer 2 — The evaluator's math ⬜ (Phase 0, substep 4b/4c)
- Stone 8 ✅ — calibration curves and reliability diagrams. Measures whether the agent's confidence language matches reality at scale. Runnable toy: `uv run python -m fingym.toys.calibration_diagram`. Full summary in Layer 2 body below.
- Stone 9 ✅ — scoreboard assembly. A table with one row per prediction and one column per scoring metric, plus metadata columns (date, horizon, expression-type, agent_id) for slicing. Kept decomposed by default; collapsed to single numbers only at explicit decision points with declared rules. Full summary in Layer 2 body below.
- Stone 10 ✅ — multi-horizon scoring (1m / 3m / 6m / 1y in parallel; horizon set is parameterizable, not hardcoded). Same decision time produces one Contract per horizon; each scored independently. The `horizon` column on the scoreboard enables per-horizon slicing for aggregation, per-horizon held-out replay at promotion, and per-horizon domain-of-validity tagging on promoted skills. Full summary in Layer 2 body below.
- Stone 11 ⬜ — expression-type tagging within `TradeAction` (action-space-aware scoring; equity-long / equity-short / option-call / option-put / option-spread / option-straddle / vol-long / vol-short / pair). `NoAction` is a typed peer of `TradeAction`, not a sub-type of it — handled by Stone 13, not folded in here.
- Stone 11a ⬜ — market-delta scoring (the agent's belief minus market-implied belief, scored against realized payoff). Distinguishes "well-calibrated but no edge" from "well-calibrated AND edge." Without this, the scoreboard cannot tell a calibrated agent that agrees with the market apart from a calibrated agent that monetizably disagrees. Operates on the `belief_delta` field of a `Contract` (see [CONTRACT.md](CONTRACT.md)). At Phase 0 the toy provides `P_market`; at Phase 2 the recovery mechanism (Stone 31) provides it for real markets.
- Stone 12 ⬜ — process-quality flag (did the agent update on emissions vs price)
- Stone 13 ⬜ — decision-quality score (action vs belief, given payoff structure), including `NoAction` as first-class. Scores: (a) did the agent correctly choose `NoAction` when calibrated `belief_delta` was below cost threshold, (b) when the agent chose `TradeAction`, did the expression match the belief shape (e.g., long-vol when belief is high-uncertainty). `NoAction` is scored separately, never collapsed to `size = 0` of a `TradeAction`. The `NoAction`-correct-when-no-edge case is explicitly rewarded — DESIGN.md Operational Constraints, BIAS_PATTERNS #12 (trade-for-trade's-sake).
- Stone 14 ⬜ — capacity-adjusted return (edge at deployable size, not nominal size)

### Layer 3 — Evaluator validated on toys ⬜ (Phase 0, substeps 5–8)
- Stone 15 ⬜ — the synthetic-market toy (hidden company state + market participant with its own belief + evidence stream that imperfectly informs both; second fixture beyond the coin). Exercises the full pipeline `P_AI(state) → P_market(state) → action → score` in toy world where the evaluator knows true state, true future path, AND the market's actual belief. Without a market in the toy, we cannot distinguish "agent calibrated about state but market also calibrated (no edge)" from "agent calibrated about state and market mispriced (real edge)" — and that distinction is what the project monetizes.
- Stone 16 ⬜ — adversarial agents (confidently-wrong, always-50%, well-calibrated)
- Stone 17 ⬜ — validating the evaluator ranks the adversaries correctly on every scoreboard dimension
- Stone 18 ⬜ — reliability diagrams as visual artifacts; the Phase 0 exit criterion
- Stone 19 ⬜ — the model interface contract (typed Protocol: raw evidence → structured `Contract` object, spec'd in [CONTRACT.md](CONTRACT.md)). Required fields at Phase 0: decision_time, evidence_ids, hidden_state_hypotheses, ai_belief, market_implied_belief (toy), belief_delta, horizon, action_or_no_action, recommended_size, falsifiers, label_plan, cognitive_audit_trail, memory_update_proposal. Deferred fields (cost, slippage, capacity, payoff_distribution, expected_log_growth_after_costs) ship with Phase 2+ machinery. Scaffolding for Layer 5.
- Stone 20 ⬜ — the memory artifact schema (versioned, model-readable, horizon/expression-tagged) — scaffolding for Layer 7
- Stone 21 ⬜ — property tests for math invariants (Bayes commutativity, Kelly monotonicity, Brier/log properness)

> *Phase 0 exit. Phase 0 is "done" when the evaluator correctly orders the three adversarial agents on every scoreboard dimension, the model interface is documented with a stub that compiles, and the memory schema validates a sample artifact.*

### Layer 4 — Point-in-time data spine + raw-evidence channel ⬜ (Phase 1)
- Stone 22 ⬜ — corpus QA (validate the existing 10-year / 1700-name transcript corpus before any data flows)
- Stone 23 ⬜ — the six data types in the canonical schema (emissions, derived_evidence, beliefs, actions, labels, scores) — derived_evidence is mechanical transformation only, never alpha cognition
- Stone 24 ⬜ — point-in-time discipline in depth (`as_of` vs `as_known`, restatements, look-ahead audits)
- Stone 25 ⬜ — replay vs live parity (the same pipeline must run both, byte-identical)
- Stone 26 ⬜ — survivorship bias and the delisted shadow universe (Norgate fundamentals for all in-scope names)
- Stone 27 ⬜ — the trajectory store as year-2 SFT fuel (every belief/action/outcome/score preserved in SFT-fit format)
- Stone 28 ⬜ — the raw-evidence channel (typed pipe delivering full unprocessed evidence to a model on demand)

### Layer 5 — Model-driven agent on raw evidence ⬜ (Phase 2)
- Stone 29 ⬜ — the pure-code plumbing baseline (hand-coded Bayesian — validates the pipeline, never promoted)
- Stone 30 ⬜ — the first model-driven agent (raw evidence in, structured terminal output out)
- Stone 31 ⬜ — market-implied belief recovery (implied DCF, options-implied probabilities, implied volatility)
- Stone 32 ⬜ — the edge calculator (your belief − market-implied belief, net of costs)
- Stone 33 ⬜ — fractional Kelly sizing (0.25× to 0.5× Kelly for miscalibration absorption)

### Layer 6 — Live operation + memory ⬜ (Phase 3)
- Stone 34 ⬜ — live-feed engineering (market hours, halts, outage handling without info leak)
- Stone 35 ⬜ — memory artifact lifecycle (proposed → probationary → promoted → retired)
- Stone 36 ⬜ — calibration diagnostics dashboard (live reliability diagram, Brier rolling average)
- Stone 37 ⬜ — no-Michael-comparison enforcement at the live layer (DESIGN.md #10 made structural)

### Layer 7 — Population + promotion gate ⬜ (Phase 4)
- Stone 38 ⬜ — population variants (≥3 agents varying in model × memory × prompt × reasoning)
- Stone 39 ⬜ — LLM as proposer of candidate memory items
- Stone 40 ⬜ — the promotion gate (held-out replay + cross-model regression + survivorship check + domain-of-validity tagging)
- Stone 41 ⬜ — Goodhart resistance via scoreboard composition (a memory item that improves only one metric is suspect)

### Apex — Year-2 own-model fine-tune ⬜ (Phase 5)
- Stone 42 ⬜ — cross-model swap test (≥2 frontier + ≥1 open-weights; promoted memory must survive)
- Stone 43 ⬜ — SFT data preparation from the trajectory store; sample fine-tune on a small open-weights model
- Stone 44 ⬜ — capacity-adjusted scoring with realistic retail market-impact assumptions
- Stone 45 ⬜ — the year-2 plan document (data accumulation targets, fine-tune triggers, deployment criteria)

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

### Stone 6 — the Brier score, formula and properties

**Formula:**

```
Brier(belief, outcome) = Σ_h (belief[h] − 1[h == outcome])²
```

For each hypothesis, take the probability the agent assigned, subtract 1 if that hypothesis is the actual outcome (0 otherwise), square it, sum across all hypotheses.

**Coin example.** Belief `{fair: 0.30, biased: 0.70}`, outcome `"biased"`:
- For `fair`: `(0.30 − 0)² = 0.09`
- For `biased`: `(0.70 − 1)² = 0.09`
- Sum: **0.18**

**Why proper.** Expected Brier `E[Brier | r] = q × 2(1−r)² + (1−q) × 2r²` is a quadratic in r with its unique minimum at `r = q`. Derivative: `−4q + 4r = 0 → r = q`. The valley always lands at the truth, regardless of `q`.

**Edge cases:**
- Max loss: **2.0** for binary (and any K). **Bounded** — never blows up.
- Min loss: 0.0 (100% on the truth).
- Cromwell case (p=0 on the truth): contributes 2.0. Loud but finite. Doesn't dominate averages the way log score does.

**In code.** `src/fingym/evaluator/scoring.py:brier()`. The `for` loop is `Σ_h`; `indicator = 1.0 if hypothesis == outcome else 0.0` is the indicator function; degenerate case (outcome not in belief's support) adds 1.0 as a full-miss penalty.

**Pairs with log score (Stone 7).** Brier is bounded → averages politely across many calls, doesn't scream at near-Cromwell. Log score is unbounded → screams. Running both catches general miscalibration AND catastrophic overconfidence.

### Stone 7 — the log score, formula and Cromwell

**Formula:**

```
log_score(belief, outcome) = −ln(belief[outcome])
```

Take the probability the agent assigned to the actual outcome, take its natural log, flip the sign. Only `belief[outcome]` from the distribution matters; everything else is ignored.

**Coin example.** Belief `{fair: 0.30, biased: 0.70}`, outcome `"biased"`:
- log_score = `−ln(0.70) ≈ 0.3567`

**Why proper.** Expected log score `E = −q ln(r) − (1−q) ln(1−r)` is U-shaped (convex) in r with unique minimum at `r = q`. Derivative `−q/r + (1−q)/(1−r) = 0 → r = q`. Same proper property as Brier; different curve shape.

**The Cromwell mechanism — built-in infinite penalty:**

- `ln(0) = −∞` → `−ln(0) = +∞`.
- Agent assigned probability 0 to the actual outcome → log score = `+∞`. **Literally infinite, not "very bad."**
- This is intentional: the math refuses to forgive an unrecoverable Bayesian failure. A probability-0 hypothesis cannot be resurrected by any future evidence; the log score forces that unrecoverability into the loss.
- Smooth approach to infinity (catches *near*-Cromwell, not just exact zero):
  - `p = 0.10` → loss 2.30
  - `p = 0.01` → loss 4.61
  - `p = 0.001` → loss 6.91
  - `p = 0` → loss `+∞`

**Edge cases:**

- Min loss: 0.0 (probability 1 on the truth).
- Max loss: **unbounded**.
- One row of `+∞` makes any mean `+∞`. Operational handling: count Cromwell violations separately, average only over non-violation rows. `+∞` IS the signal, not an average input.

**In code.** `src/fingym/evaluator/scoring.py:log_score()`. `belief.get(outcome, 0.0)` pulls the probability; returns `math.inf` if zero-or-missing; otherwise `−math.log(probability)`. The `math.inf` IS the Cromwell signal — downstream code is responsible for handling it loudly.

**Brier vs log score, side by side:**

| Property | Brier | log score |
|---|---|---|
| Inputs used | whole distribution | only `belief[outcome]` |
| Max loss | 2.0 (bounded) | `+∞` (unbounded) |
| At Cromwell | 2.0 | `+∞` |
| Averaging | smooth | one bad row dominates |
| Best for | general miscalibration | near-Cromwell detection |

Both proper. Both reward `r = q`. Run both — different failure modes surface in different columns.

---

### Stone 7a — the four-thing decomposition (bridge to Layer 2)

In Layer 1 the game had two players: agent vs reality. **Layer 2 adds a third: the market.** Stone 7a is the vocabulary that makes the three-player game explicit.

**Four primitives.** All separate. All per-horizon.

- **`S_true`** — what's actually true. One value from a fixed set of hypotheses (e.g., `{strengthening, stable, decaying}`). Revealed at the horizon; not known at decision time.
- **`P_AI(S)`** — the agent's belief. Distribution over the same set, sums to `1`. The thing Layer 1 scored.
- **`P_market(S)`** — the market's belief. Distribution of identical shape. Not announced directly; recoverable from observable prices (Phase 2 mechanism, Stone 31). Toy worlds construct it directly.
- **`Action(A)`** — the action. Typed sum: `TradeAction(...) | NoAction`. `NoAction` is a peer of `TradeAction`, not a sized-down version.

**Derived symbol.** `belief_delta(S) = P_AI(S) − P_market(S)`. The gap, per state. Signed real per state; sums to zero across states. The evaluator focuses on `belief_delta(S_true)` — the gap on the realized truth.

**Anchor.**

> Money lives in `belief_delta = P_AI(S) − P_market(S)` only when an `Action(A)` exists whose payoff distribution monetizes that gap after costs, **and the realized `S_true` validates the side the agent took.**

Four conditions, all required: disagreement (gap ≠ 0), agent correct (gap positive on truth, not negative), actionable (an `Action(A)` exists), survives costs. If any link fails, no edge.

**The Layer-2 reframe.** Layer 1 scored `P_AI` alone. Layer 2 stones each measure one aspect of the four primitives:

| Stone | What it measures |
|---|---|
| 8 calibration curves | Does `P_AI(S)` track `S_true` at the bucket level? |
| 9 scoreboard | All metrics per `Contract`, kept as columns |
| 10 multi-horizon | The four primitives, per horizon, scored independently |
| 11 expression types | Which `TradeAction(A)` sub-type was chosen? |
| 11a market-delta | Score `belief_delta(S_true)` — the gap on the truth |
| 12 process-quality | Did `P_AI(S)` update on emissions, or drift to track `P_market(S)`? |
| 13 decision-quality | Given `P_AI`, `P_market`, costs, did `Action(A)` make sense? `NoAction` rewarded when gap < costs |
| 14 capacity-adjusted | At deployable size, does the gap survive market impact? |

**Why "no edge" is a typed first-class output.** Most of the time, `belief_delta ≈ 0` (agreement) or `|belief_delta| < costs`. The correct `Action(A)` is `NoAction`. The system rewards saying "no edge" accurately. BIAS_PATTERNS #12 (trade-for-trade's-sake) names the failure of an agent that always finds trades.

**Runnable toy.** Three scenarios — calibrated+monetizable, calibrated+no-gap, confident+wrong+big-gap — on actual numbers, with the four primitives computed for each. Brier alone cannot distinguish them; the four-thing scoreboard can.

```bash
uv run python -m fingym.toys.four_thing_decomp
```

Source: [src/fingym/toys/four_thing_decomp.py](src/fingym/toys/four_thing_decomp.py).

**What's deliberately unanswered.** Stone 7a is vocabulary. Stones 8–14 measure with it. Stone 31 (Phase 2) implements `P_market(S)` recovery from real markets. Formal symbol definitions, ranges, and properties live in [FORMULAS.md](FORMULAS.md).

---

**Layer 1 — atom of inference — complete (with Stone 7a as bridge to Layer 2).** Belief, outcome, label, score signature, why-belief-not-outcome, properness, Brier, log score, four-thing decomposition. The Layer-1 scoring functions are implemented in `src/fingym/evaluator/scoring.py` (substep 4a); the four-thing decomposition is demonstrated in `src/fingym/toys/four_thing_decomp.py`. Next: **Layer 2 — the evaluator's math** (calibration curves, scoreboard assembly, multi-horizon and expression-type aggregation, plus market-delta and NoAction-first-class decision quality per v2).

---

---

## Layer 2 — The evaluator's math

### Stone 8 — calibration curves and reliability diagrams

**The question.** When the agent says "X percent confident," does the truth actually happen X percent of the time?

This cannot be answered from any single prediction. It is a statistical property of the agent visible only across many predictions.

**The procedure — count, group, compare.** Given many predictions from one agent with their actual outcomes:

1. **Group** predictions by the claim. All predictions where the agent said ~40%. All where it said ~70%. Etc.
2. For each group, compute two numbers: **Mean claim** (what the agent said, averaged) and **Observed rate** (fraction of those predictions where the positive outcome actually happened).
3. If claim ≈ observed, the agent is calibrated for that group.
4. If claim > observed, the agent is overconfident in that group.
5. If claim < observed, the agent is underconfident in that group.

**Worked example.** Three adversarial agents, 200 binary events each (true probabilities mixed from {40%, 60%, 80%}; base rate ≈ 60%). Runnable toy: `uv run python -m fingym.toys.calibration_diagram`.

**Agent W (well-calibrated, says true probability):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 40-50% | 73 | 40.0% | 34.2% | 5.8 |
| 60-70% | 65 | 60.0% | 66.2% | 6.2 |
| 80-90% | 62 | 80.0% | 74.2% | 5.8 |

Calibration error: **5.9 pp**. Small gaps in every bucket — sampling noise from only 200 events. The agent is calibrated.

**Agent O (confidently-wrong, pushes claims to extremes 10% or 90%):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 10-20% | 73 | 10.0% | 34.2% | 24.2 |
| 90-100% | 127 | 90.0% | 70.1% | 19.9 |

Calibration error: **21.5 pp**. When O said 90%, reality was only 70%. When it said 10%, reality was 34%. Big gaps in both directions.

**Agent U (always-50%, ignores evidence):**

| Bucket | # events | Mean claim | Observed | Gap |
|---|---:|---:|---:|---:|
| 50-60% | 200 | 50.0% | 57.0% | 7.0 |

Calibration error: **7.0 pp**. One bucket. Agent has no discriminative value — it cannot distinguish a 40% event from an 80% event.

**The single-number summary (Expected Calibration Error, ECE).** Weighted average of bucket gaps: per bucket, multiply gap by # events; sum across buckets; divide by total events. One number per agent that ranks them.

**Important limitation.** ECE is a summary; the reliability table is the diagnostic. Agent U's ECE (7.0) looks similar to W's (5.9), but U's single-bucket structure gives the game away. **Calibration alone is necessary, not sufficient.** Combine with Layer-1 scoring rules (Brier, log score) to catch uninformative agents that have low ECE by accident.

**The three classic signatures:**

| Signature | What the table shows | Reading |
|---|---|---|
| Calibrated | Many buckets, claim ≈ observed each row | Trustable across confidence levels |
| Overconfident | Buckets at extremes (10%, 90%) with claim much higher than observed | When agent says 90%, treat it as ~70% |
| Underconfident | Buckets where claim < observed | Agent is hedging; could have claimed more |
| Uninformative | One bucket only; observed ≈ base rate | Useless even if ECE is low |

**Connection to Layer 1.** Layer 1 scored P_AI on single predictions (Brier, log score per row). Stone 8 scores P_AI across many predictions. Both are about the agent's belief in isolation. Stone 11a will introduce the gap between P_AI and P_market.

**Runnable toy.** [src/fingym/toys/calibration_diagram.py](src/fingym/toys/calibration_diagram.py). Try: change `true_probs = [0.4, 0.6, 0.8]` to `[0.2, 0.5, 0.8]` — base rate becomes 50%, agent U's ECE drops near zero, and U *looks* calibrated even though it has zero discrimination. That's the discrimination point made vivid.

**Formal symbols.** Reference notation lives in [FORMULAS.md](FORMULAS.md) under "Calibration measurement (Stone 8)." Not needed for understanding; provided for code/agent reference.

### Stone 9 — scoreboard assembly

**The data structure.** The evaluator's output is a **table**. One row per prediction (one `Contract`). One column per scoring metric. Plus metadata columns for slicing — date, agent_id, horizon, expression-type, sector. Production scoreboards have many columns; the schema grows as each Layer-2 stone adds its metric.

**Example shape** (six columns shown; the real one is wider):

| Prediction ID | Date | Agent's claim | What happened | Brier | log_score |
|---|---|---|---|---:|---:|
| pred_001 | 2026-05-15 | 70% biased | biased | 0.18 | 0.36 |
| pred_002 | 2026-05-16 | 50% biased | fair | 0.50 | 0.69 |
| pred_003 | 2026-05-17 | 99% biased | biased | 0.0002 | 0.01 |
| pred_004 | 2026-05-18 | 30% biased | biased | 0.98 | 1.20 |

That's it. A spreadsheet of evaluation results.

**Why we keep it decomposed (do NOT routinely collapse to one number):**

- **Different columns catch different failure modes.** Brier catches moderate overconfidence; log score catches near-Cromwell; calibration error catches systematic skew. Each column lights up red for a different kind of failure. Averaging them washes out the signal.
- **Goodhart resistance.** A single optimization target gets gamed. Multiple parallel metrics under different proper scoring rules cannot all be gamed simultaneously without honest reporting. One column = one thing to fool; many columns = harder to fool.

**Two kinds of operations on the scoreboard:**

- **Aggregate per column.** Mean Brier across all rows. Mean log score (filtering out Cromwell rows). ECE per bucket. Count of rows where Brier < 0.1. Each aggregation is per column; columns stay separate.
- **Slice by metadata.** "Mean Brier on 6-month horizon predictions only" — filter rows by horizon, then mean. "Calibration error in tech sector vs financial sector" — filter, compute per slice. Same scoreboard, different slices answer different questions.

**When to collapse to a single number — only at specific decision points with explicit rules.** Example promotion rule:

> Promote a memory item to L3 if and only if its addition improves Brier by ≥5% AND doesn't worsen log score AND doesn't widen any calibration bucket gap by more than 3 percentage points.

That's three columns with three thresholds. The collapse rule is written down. The scoreboard itself stays decomposed. From intuitions.md #2: "Collapse to a scalar only at decision points, and make the collapse rule explicit."

**How Stones 10–14 use this scoreboard:**

- Stone 10 (multi-horizon) — adds a `horizon` column; runs aggregations per horizon slice.
- Stone 11 (expression-type) — adds an `expression_type` column; aggregations per action type.
- Stone 11a (market-delta) — adds a `belief_delta_on_truth` column.
- Stones 12, 13, 14 — each add their column.

The scoreboard schema is locked at the structural level here; columns grow as each stone lands.

**Connection to memory architecture.** Scoreboard rows are L0 trajectory records (see [memory-design.md](memory-design.md)). Immutable, append-only, point-in-time. Aggregations are computed *from* the immutable rows; no row is ever updated in place.

**In code.** Schema lives in `src/fingym/evaluator/scoreboard.py` (Phase 0 substep 4b/4c deliverable). Row construction at evaluation time; aggregations and slicing performed by the evaluator's reporting layer.

**One sentence.** The scoreboard is a table — one row per prediction, one column per scoring metric, plus metadata columns for slicing. Decomposed by default. Collapse only at explicit decision points with declared rules.

### Stone 10 — multi-horizon scoring

**The reframe.** "What is the hidden state?" is an incomplete question. The complete question is **"what is the hidden state, over this time window?"** Strengthening over the next month (cyclic dynamics) and strengthening over the next year (strategic positioning) are different claims about different things.

**The mechanic.** A single decision-time produces multiple `Contract` objects — one per horizon the agent cares about. Each gets its own row in the scoreboard, distinguished by the `horizon` column.

Example: agent's beliefs about AAPL at 2026-05-15:

| Decision time | Company | Horizon | P_AI(strengthening) | Scored against |
|---|---|---|---:|---|
| 2026-05-15 | AAPL | 1m | 60% | AAPL's state at 2026-06-15 |
| 2026-05-15 | AAPL | 3m | 55% | AAPL's state at 2026-08-15 |
| 2026-05-15 | AAPL | 6m | 40% | AAPL's state at 2026-11-15 |
| 2026-05-15 | AAPL | 1y | 30% | AAPL's state at 2027-05-15 |

Four rows. Same agent. Same company. Same decision time. Four different futures to score against.

**The discovered fact.** After running over time, the scoreboard's horizon slices tell you where each agent's edge lives:

| Per-horizon performance | Brier | log_score | Calibration error |
|---|---:|---:|---:|
| 1m | 0.18 | 0.32 | 4 pp |
| 3m | 0.21 | 0.40 | 6 pp |
| 6m | 0.35 | 0.65 | 14 pp |
| 1y | 0.42 | 0.85 | 22 pp |

This agent is sharp at short horizons and degrades at long ones. That's a discovered fact, not a pre-commitment. The system never pre-commits to "we are a quarterly system" or "we are a year-horizon system." It discovers per-agent, per-sector, per-skill where edge actually lives. (DESIGN.md "Operational Constraints" — multi-horizon scoring.)

**Per-horizon promotion gate.** The four-check promotion gate (DESIGN.md #4) runs **per horizon, independently.** A candidate skill is promoted with `horizon: [list]` in its domain-of-validity listing the specific horizons where all four checks passed:

| Check at horizon | 1m | 3m | 6m | 1y |
|---|:---:|:---:|:---:|:---:|
| Held-out calibration improves | ✓ | ✓ | ✓ | ✗ |
| Cross-model (≥2 engines) | ✓ | ✓ | ✓ | (n/a) |
| Survivorship check | ✓ | ✓ | ✓ | (n/a) |

→ Promoted with `horizon: [1m, 3m, 6m]`. **Excluded from 1y context** by the domain-of-validity filter. At inference time, an agent operating at 1y horizon never sees this skill.

This is what prevents the "skill that worked at 3m leaks into 1y and corrupts long-horizon calls" failure mode. The horizon column on the scoreboard is what enables both per-horizon promotion testing and per-horizon inference-time filtering.

**Parameterizable.** The set of horizons is configurable per agent or per evaluator run, not hardcoded. Standard set: `{1m, 3m, 6m, 1y}`. Toys may use shorter horizons (days or flips) for fast iteration. New horizons can be added without architectural change.

**Connection to memory architecture.** Per [memory-design.md](memory-design.md), every L3 promoted skill carries its horizon list. Per [CONTRACT.md](CONTRACT.md), every Contract carries a horizon field. Per the Stone 9 scoreboard schema, every row carries a horizon column. The three structures align by design.

**No new structural machinery.** Multi-horizon scoring is the Stone 9 scoreboard *used correctly* — slicing by an existing column. The conceptual move is bigger than the implementation: state is per-horizon by default; the agent's job is per-horizon forecasting; the evaluator's job is per-horizon scoring.

**One sentence.** The same belief means different things at different horizons; the agent emits one Contract per horizon; the scoreboard scores each independently; the system discovers where each agent's edge lives empirically — and the per-horizon promotion gate ensures skills only act where they're validated.

---

*Higher layers (2 through Apex) are itemized stone-by-stone in the table of contents at the top of this document. Detailed summaries land here as each stone is taught.*
