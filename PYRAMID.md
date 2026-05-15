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

**Current position:** Layers 1 and 2 complete. Stones 1–7 (atom of inference), 7a (four-thing decomposition bridge), 8–14 (evaluator's math: calibration, scoreboard, multi-horizon, expression-type, market-delta, process-quality, decision-quality with NoAction as peer, capacity-adjusted return) all taught and distilled. Next: **Layer 3 — evaluator validated on toys** (Stones 15–21, Phase 0 substeps 5–8): synthetic-market toy, adversarial agents, evaluator validation, reliability diagrams as visual exit criterion, model interface contract, memory artifact schema, property tests. Phase 0 exit is at the end of Layer 3.

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
- Stone 7a ✅ — **the four-thing decomposition** (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`). Bridge from Layer 1 to Layer 2: Layer 1 scored a belief vs reality; Layer 2 scores a belief vs a *competing belief* (the market's), arbitrated by reality. Anchor: money lives in `P_AI - P_market` only when an `Action(A)` monetizes it after costs *and* `S_true` validates the side. Symbols in [FORMULAS.md](FORMULAS.md). Full distilled summary in Layer 1 body below.

### Layer 2 — The evaluator's math ⬜ (Phase 0, substep 4b/4c)
- Stone 8 ✅ — calibration curves and reliability diagrams. Measures whether the agent's confidence language matches reality at scale (across many predictions, grouped by claimed confidence). Full summary in Layer 2 body below.
- Stone 9 ✅ — scoreboard assembly. A table with one row per prediction and one column per scoring metric, plus metadata columns (date, horizon, expression-type, agent_id) for slicing. Kept decomposed by default; collapsed to single numbers only at explicit decision points with declared rules. Full summary in Layer 2 body below.
- Stone 10 ✅ — multi-horizon scoring (1m / 3m / 6m / 1y in parallel; horizon set is parameterizable, not hardcoded). Same decision time produces one Contract per horizon; each scored independently. The `horizon` column on the scoreboard enables per-horizon slicing for aggregation, per-horizon held-out replay at promotion, and per-horizon domain-of-validity tagging on promoted skills. Full summary in Layer 2 body below.
- Stone 11 ✅ — expression-type tagging within `TradeAction`. Same belief can be expressed many ways (equity-long, option-call, option-spread, vol-long, pair, etc.) with different payoff structures. The scoreboard carries `expression_type` as the broad category; specific trade details (strike, expiration, size, premium) live inside the `TradeAction` object on the Contract. Per-expression-type promotion gate. `NoAction` is a typed peer, not folded here. Full summary in Layer 2 body below.
- Stone 11a ✅ — market-delta scoring. The first scoreboard column that takes `P_market` into the math. Per-row value: `belief_delta_on_truth = P_AI(S_true) - P_market(S_true)`. Positive = monetizable edge; zero = no edge; negative = anti-edge. Distinguishes the three situations Layer 1 alone cannot see. Full summary in Layer 2 body below.
- Stone 12 ✅ — process-quality flag (narrow form). Single mechanical check per update: was there an emission (transcript, filing, fundamental release, news event) with `as_known` in the time window before this update? If yes, `motivated`. If no, `unmotivated` — agent updated with nothing new in the world to react to. Per-agent aggregate `unmotivated_update_rate`; promotion gate caps it (initial value: 10%). Does NOT attempt to judge WHICH evidence the agent used when both emission and price are present — that distinction collapses in reality because price IS the market's update on the emission. The sophisticated price-tracker that waits for an emission then mirrors the market is caught by Stone 11a (`belief_delta_on_truth ≈ 0` by construction), not by Stone 12. Full summary in Layer 2 body below.
- Stone 13 ✅ — decision-quality score with `NoAction` as first-class peer. Three coherence checks on the action vs the inputs (belief, gap, costs) at decision time: **threshold-match** (trade iff gap > cost), **direction-match** (trade is on the right side of the gap), **expression-match** (expression type fits belief shape). Each Contract gets a coherence verdict and three independently stored sub-flags. `decision_quality_rate` is a scoreboard column, NOT a hard cap — incoherent decisions can be legitimate (crowding, hedging, atypical vol pricing) and the promotion gate weighs the column alongside `belief_delta` and held-out return. The lazy agent (always NoAction) is caught by combining with Stone 11a (near-zero mean gap). Full summary in Layer 2 body below.
- Stone 14 ✅ — capacity-adjusted return. Per-Contract `realized_edge = nominal_edge − spread − commission − market_impact(size, ADV) − alpha_decay`. Square-root law for impact: impact grows with `sqrt(size / ADV)`. Aggregated as `mean_realized_edge` and the diagnostic ratio `realized_to_nominal`. Sliced primarily by **deployable size bucket** — different agents have different capacity profiles, and the gate evaluates per-size, not just per-aggregate. Column on scoreboard, NOT a hard cap (capacity is niche-specific) — with one near-tautological structural check: realized edge at the agent's stated size must be positive (otherwise it's not edge, it's a losing strategy). Full summary in Layer 2 body below.

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

**What's deliberately unanswered.** Stone 7a is vocabulary. Stones 8–14 measure with it. Stone 31 (Phase 2) implements `P_market(S)` recovery from real markets. Formal symbol definitions, ranges, and properties live in [FORMULAS.md](FORMULAS.md).

---

**Layer 1 — atom of inference — complete (with Stone 7a as bridge to Layer 2).** Belief, outcome, label, score signature, why-belief-not-outcome, properness, Brier, log score, four-thing decomposition. The Layer-1 scoring functions are implemented in `src/fingym/evaluator/scoring.py` (substep 4a). Next: **Layer 2 — the evaluator's math** (calibration curves, scoreboard assembly, multi-horizon and expression-type aggregation, plus market-delta and NoAction-first-class decision quality per v2).

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

**Worked example.** Three adversarial agents, 200 binary events each (true probabilities mixed from {40%, 60%, 80%}; base rate ≈ 60%).

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

**Column-on-scoreboard vs hard-cap-on-column — the default and the exception.**

When a new scoring metric is added, the default is: it becomes a **column** that the promotion gate weighs alongside other columns. A weak number on one column can be redeemed by strong numbers elsewhere; the gate is the combination rule, not any single column.

A **hard cap** (the metric must be above/below a fixed number, or the agent is rejected outright regardless of other scores) is a stronger move. It says: there is no compensating virtue for failing this metric. Reserve hard caps for the narrow case where this is genuinely true.

Two worked examples from Layer 2:

- Stone 12's `unmotivated_update_rate` — hard-capped at 0.10. There is no compensating virtue for "agent issued an update with no new evidence in the world." It's price-following structurally, and no amount of good output redeems it.
- Stone 13's `decision_quality_rate` — column, NOT a hard cap. An incoherent-looking decision can be legitimate (crowding, hedging, atypical vol pricing) because the three mechanical coherence checks don't model every real factor. The gate considers it alongside `belief_delta` and held-out return; an agent can score modestly on Stone 13 and still be the right one to promote if its other columns are strong.

The shape of the question for any new metric: "Is there ANY legitimate reason an agent might score poorly on this and still be a better agent than one that scores well?" If yes → column. If no → hard cap is on the table.

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

### Stone 11 — expression-type tagging within `TradeAction`

**The setup.** When the agent decides to trade, it must also choose **how** to express its belief. The same belief ("AAPL is strengthening") can be expressed many different ways — each with a different payoff profile under each outcome.

**The expression-type categories** (what the `expression_type` column on the scoreboard records):

| `expression_type` | Payoff shape |
|---|---|
| `equity-long` / `equity-short` | Linear in price move; symmetric upside/downside |
| `option-call` / `option-put` | Asymmetric; capped downside (premium paid), big upside above/below strike |
| `option-spread` | Asymmetric with both upside and downside capped; cheaper than naked option |
| `option-straddle` / `option-strangle` | Profits from large moves in either direction |
| `vol-long` / `vol-short` | Profits from realized vs implied volatility difference, regardless of direction |
| `pair` / `relative-value` | Profits from one underlying outperforming another; hedged against market direction |

**Critical distinction — category vs full spec.** `expression_type` on the scoreboard is the **broad category**. The specific trade details — underlying, strike, expiration, premium, direction (long or short the contract), size — live **inside the `TradeAction` object** on the Contract. Example:

```
TradeAction {
  expression_type: "option-call"          ← scoreboard column captures THIS
  underlying:      "AAPL"
  direction:       "long"
  strike:          210
  expiration:      "2026-08-15"
  size:            10  contracts
  premium_paid:    $250  per contract
}
```

The scoreboard slices on the category because that's where statistical power lives. The full spec lives on the Contract for payoff math (Stones 13 and 14).

**Why category-level slicing.** With ~hundreds of trades over a year, you have many trades per category but few per specific strike-expiration combo. Slicing at the category level gives you statistical reads like *"this agent's mean Brier on option-call trades is 0.21; on equity-long trades is 0.18"* — meaningful comparisons. Slicing at the strike-by-strike level would give one row per unique trade, no aggregation possible.

**Per-expression-type promotion gate.** Same shape as Stone 10's per-horizon gate. A candidate skill is tested per expression type:

| Check at expression type | equity-long | option-call | vol-spread | pair |
|---|:---:|:---:|:---:|:---:|
| Held-out calibration improves | ✓ | ✓ | ✗ | ✓ |
| Cross-model regression | ✓ | ✓ | (n/a) | ✓ |
| Survivorship check | ✓ | ✓ | (n/a) | ✓ |

→ Promoted with `expression_type: [equity_long, option_call, pair]`. Excluded from `vol-spread` context by the domain-of-validity filter. **A skill that doesn't validate at a given expression doesn't get to act there.** Prevents the "skill that worked on equity-direction leaks into options-trading" failure mode.

**`NoAction` is a typed peer of `TradeAction`, not an expression type.**

```
Agent's action layer:
  ├── TradeAction
  │     ├── equity-long / equity-short
  │     ├── option-call / option-put / option-spread / option-straddle
  │     ├── vol-long / vol-short
  │     └── pair / relative-value
  └── NoAction  (← peer, not a sub-type; scored by Stone 13)
```

`NoAction` is scored on whether the agent correctly recognized the absence of edge — a different scoring path from any `TradeAction` (which is scored against a payoff structure). BIAS_PATTERNS #12 (trade-for-trade's-sake) is the defense `NoAction` provides.

**Stacking with Stone 10.** A skill's domain-of-validity can carry BOTH `horizon: [list]` AND `expression_type: [list]` AND `sector: [list]`. Three independent slicing dimensions. A skill might be valid only at `horizon: [3m, 6m]` AND `expression_type: [equity_long]` AND `sector: [tech_hardware]` — narrowly tagged, narrowly applied. Prevents leakage across dimensions.

**Connection forward.** Stone 13 (decision-quality) will use the *full* `TradeAction` details (strike, expiration, premium, etc.) to score whether the chosen specific trade matched the belief and the cost structure. Stone 14 (capacity-adjusted return) will use the same details to compute realistic P&L at deployable size.

**In code.** `expression_type` is a string field on the scoreboard row (Stone 9 schema); `TradeAction` is the typed sum from [CONTRACT.md](CONTRACT.md). The full `TradeAction` object is stored alongside the scoreboard row for downstream payoff computation.

**One sentence.** `TradeAction` has sub-types (equity-long, option-call, vol-spread, pair, …); `expression_type` on the scoreboard is the broad category for slicing; specific trade details live inside the `TradeAction` object; per-expression-type promotion gate ensures skills only act in expression contexts where they've been validated; `NoAction` is a typed peer of `TradeAction`, handled by Stone 13.

### Stone 11a — market-delta scoring

**Why this stone is load-bearing.** Stones 6-10 measured the agent's belief in isolation. Brier, log score, calibration error — all use only `P_AI` and `S_true`. None of them know `P_market` exists. So a calibrated agent that agrees with the market and a calibrated agent that disagrees with the market on the right side get identical Layer-1 scores. **Edge is invisible to Layer 1.**

Stone 11a is the first column on the scoreboard that takes `P_market` into the math, making the four-thing decomposition's monetization layer measurable.

**The value computed per row.** For each Contract, the `belief_delta_on_truth` column stores:

```
P_AI(S_true) - P_market(S_true)
```

Signed gap. Positive means the agent was more confident on the truth than the market (edge). Zero means agreement (no edge). Negative means anti-edge (market saw it, agent didn't).

**Worked example (from the runnable toy).** Same agent belief `{strengthening: 0.55, stable: 0.30, decaying: 0.15}`; same outcome `S_true = strengthening`. Only `P_market` varies.

| Scenario | `P_market(strg)` | Brier | log_score | Gap on truth |
|---|---:|---:|---:|---:|
| A: market bearish (real edge) | 30% | 0.3150 | 0.5978 | **+0.25** |
| B: market agrees (no edge) | 55% | 0.3150 | 0.5978 | **0.00** |
| C: market more confident (anti-edge) | 80% | 0.3150 | 0.5978 | **-0.25** |

Brier and log_score IDENTICAL across all three. Gap column is what reveals the three different edge signatures. Layer 1 alone cannot distinguish them; Stone 11a can.

**Two more revealing cases (also in the toy).** Agent confidently wrong on the truth: `{strengthening: 0.05, stable: 0.15, decaying: 0.80}`, same `S_true = strengthening`.

| Scenario | `P_market(strg)` | Brier | log_score | Gap on truth |
|---|---:|---:|---:|---:|
| D: wrong + big disagreement (catastrophic) | 30% | 1.5650 | 2.9957 | **-0.25** |
| E: both wrong + agree (no edge to lose) | 5% | 1.5650 | 2.9957 | **0.00** |

D has three corroborating red flags (Brier max, log near-Cromwell, anti-edge gap). E has the same Layer-1 catastrophe but zero gap — the market was equally wrong, so there was no informational edge to lose. **Same Layer-1 signals; very different Layer-2 interpretation.** Stone 11a is what makes that distinction.

**Aggregating across many rows.** Mean `belief_delta_on_truth` over time tells you whether the agent has systematic edge:

| Mean Gap on truth | Interpretation |
|---:|---|
| > 0 (positive) | Agent systematically right where the market is wrong. Real edge over time. |
| ≈ 0 | Agent systematically agrees with market. No informational edge — uninformative. |
| < 0 (negative) | Agent systematically less confident on truth than market. Anti-edge — losing to smarter counterparties. |

**The promotion-gate implication.** A candidate skill is judged not only on whether it improves calibration (Brier, log score) but on whether it improves mean Gap on truth. A skill that makes the belief better-shaped but doesn't change the gap isn't producing edge. A skill that increases the gap on the truth IS — even if its calibration improvement is modest. The two signals can move independently.

**The Layer-2 picture now (after Stone 11a):**

| Column | Sees | What it catches |
|---|---|---|
| Brier | P_AI, S_true | General miscalibration of belief |
| log_score | P_AI, S_true | Near-Cromwell (confident-wrong on truth) |
| **belief_delta_on_truth** | **P_AI, P_market, S_true** | **Edge / anti-edge / no-edge** |

Three orthogonal signals. No single column suffices. Each lights up red for a different failure mode.

**`P_market` source — toy vs production.** At Phase 0 (toys), `P_market` is constructed directly by the test scaffold. At Phase 2 (real markets), `P_market` is recovered from observable prices/options/spreads via the inversion mechanism (Stone 31). The recovery is approximate, but even approximate `P_market` is enough to surface the structural gap.

**What Stone 11a does NOT do.** It measures the *potential* edge — the gap between agent and market beliefs. It does not yet account for:
- Whether the agent chose an action that monetizes the gap (Stone 13).
- Whether costs and capacity allow the gap to be realized (Stone 14).
- Whether the agent updated `P_AI` on emissions vs price (Stone 12 — process quality).

The gap is necessary for edge; subsequent stones add the sufficient conditions.

**One sentence.** Stone 11a adds the first scoreboard column that takes `P_market` into the calculation; per-row value is the signed gap `P_AI(S_true) - P_market(S_true)`; positive means real edge, zero means agreement (no edge), negative means anti-edge; aggregating mean gap across many predictions reveals whether the agent has systematic edge — a signal Layer 1 calibration alone cannot detect.

### Stone 12 — process-quality flag (narrow form)

**Why this stone exists.** Stones 6–11a measure WHAT the agent produced — its belief, its gap from the market, its action. None fires at update time, before the horizon closes; all need an outcome to score against. Stone 12 fires the moment the agent emits an update and asks one mechanical question that doesn't need the outcome: **was there anything new in the world for the agent to react to?**

**The failure mode being defended.** A pure tape-reader has no information source other than the price tape. It will issue belief updates triggered by chart patterns, options-skew shifts, technical breakouts — with nothing in the underlying world having changed. Output-side scoring (Brier, log score, Stone 11a's `belief_delta_on_truth`) will eventually mark it as no-edge, but that takes the full horizon to resolve. Stone 12 catches the structural symptom at process time.

**The one signal.** For each belief update:

```
emission_in_window = True iff at least one emission row exists with
                     as_known timestamp in (prior_update_time, this_update_time]
```

`motivated` if `emission_in_window = True`. `unmotivated` if `emission_in_window = False`. That's the whole tag. Purely mechanical — a database query on the emissions table, no reasoning-trace inspection, no judgment about what the agent did with the evidence.

**What this deliberately does NOT do.** When an emission IS present, Stone 12 makes no claim about whether the agent used the emission's content, the price reaction, or both. That distinction collapses in reality: the price reaction IS the market's instant Bayesian update on the same emission, so an agent that incorporates both is reading two views of the same disclosure, not two independent signals. Trying to score "good citation vs bad citation" from reasoning-trace text would false-flag the common case where emission and price co-occur. Stone 12 leaves that judgment to the output-side scoring.

**Worked example — one agent watching AAPL over a quarter.**

Eight belief updates over 90 days. For each, the evaluator checks the emissions table for the pre-update window:

| # | Date | Emission in window? | Tag |
|---|---|---|---|
| 1 | 2026-02-12 | 10-Q filed 2026-02-11 | motivated |
| 2 | 2026-02-15 | none | unmotivated |
| 3 | 2026-02-28 | analyst day 2026-02-27 | motivated |
| 4 | 2026-03-04 | none | unmotivated |
| 5 | 2026-03-12 | supply-chain release 2026-03-11 | motivated |
| 6 | 2026-03-20 | none | unmotivated |
| 7 | 2026-04-08 | earnings call 2026-04-08 | motivated |
| 8 | 2026-04-22 | competitor 8-K 2026-04-21 | motivated |

Five motivated, three unmotivated. Three updates fired with nothing new in the world — those are the ones that need explanation.

**Per-agent aggregation.**

```
unmotivated_update_rate = (# unmotivated updates) / (total updates)
```

For this agent: 3 / 8 = **0.375**. Compared across agent types:

| Agent | Updates | Motivated | Unmotivated | Rate | Read |
|---|---:|---:|---:|---:|---|
| Disciplined reasoner | 12 | 11 | 1 | 0.083 | Updates almost exclusively on disclosures |
| Mixed agent (above) | 8 | 5 | 3 | 0.375 | Reacting to price too often |
| Tape-reader | 20 | 4 | 16 | 0.800 | Pure price-following |
| Update-spammer | 50 | 8 | 42 | 0.840 | Update spam, no discipline |

**The promotion-gate role.** Hard cap on `unmotivated_update_rate` (initial value: **0.10**). An agent that updates more than 10% of the time with no emission in window cannot be promoted regardless of output scores. The reasoning is structural: those updates have no evidence basis other than the tape, and the agent that issues them is doing reflection, not inference.

**Why the narrow form is enough.** The price-tracking failure has two faces:

1. **Pure tape-reader** — updates with no emission in window. Caught here. Mechanical and fast.
2. **Sophisticated tape-reader** — waits for an emission to land, then publishes a belief that mirrors the market's instant reaction. `emission_in_window` is True for these, so Stone 12 says nothing. But `P_AI ≈ P_market` by construction, so `belief_delta_on_truth ≈ 0`, and Stone 11a marks it as no-edge once outcomes resolve.

Stone 12 catches face (1) at update time. Stone 11a catches face (2) at horizon. Together they bracket the failure mode without needing to inspect reasoning traces or run ablations.

**Why the citation-check version was wrong.** The earlier draft of Stone 12 tried to distinguish `emission_driven` from `price_driven` by inspecting the agent's `cognitive_audit_trail` for what it cited. That breaks in the common case: emissions cause price moves, the market's reaction IS information about how surprising the disclosure was, and an agent that reads both isn't doing anything wrong. Most legitimate updates would have been flagged as ambiguous, and the threshold for handling ambiguous rows was arbitrary in every direction. The narrow form sidesteps the entire problem by only asking the mechanical question that has a defensible answer.

**Connection to intuitions.md #13** ("update on emissions, not on price"). The narrow form is the only piece of this intuition that's cleanly operationalizable. The full intuition — "weight the emission more than the price" — is enforced indirectly through Stone 11a, not through process inspection.

**Connection to Stone 11a.** Complementary, not redundant. Stone 12 fires at process time and is binary; Stone 11a fires at horizon and is continuous. An agent with low `unmotivated_update_rate` AND positive mean `belief_delta_on_truth` is doing real inference. Either alone is insufficient.

**What Stone 12 stores on the scoreboard.**

```
emission_in_window: bool
motivated_flag:     Literal["motivated", "unmotivated"]
emission_ids:       list[UUID]   # the emission rows in the pre-update window, if any
```

No verdict about how the agent used those emissions. The emission ids are stored for downstream forensics (which disclosures preceded this update) but not interpreted by Stone 12 itself.

**One sentence.** Stone 12 reduces to a single mechanical check at update time — was there an emission in the window before this update? — flags unmotivated updates as suspect, caps the per-agent rate at promotion, and leaves all judgments about which evidence the agent weighted to the output-side scoring that Stone 11a already provides.

**Two parked architectural questions (not yet decided — see [DECISIONS.md](DECISIONS.md) "Open architectural questions").**

1. **Trigger architecture — emission-triggered (A) vs agent-driven (B).** The narrow form above is Architecture B. Tentative lean: Architecture A, in which Contracts without a `triggering_emission_id` are structurally rejected and Stone 12 collapses to a one-line gate. Decision lands when Layer 4 emissions schema is built (Stone 22–23).
2. **Emissions taxonomy.** "Emission" is broader than company-specific filings. The taxonomy includes direct (company), sector (peers / suppliers / customers), macro (rates, CPI, NFP, geopolitical), and cross-asset (commodities, FX, credit). Each emission row carries scope metadata identifying which underlyings it applies to. A Fed 100 bps move is ONE emission row in scope for hundreds of names. Schema lands with Stone 22–23.

Both are parked with explicit revisit triggers in DECISIONS.md. Stones 13 onward proceed under the working assumption that Architecture A is in force and "emission" means the full taxonomy.

### Stone 13 — decision-quality with NoAction as first-class peer

**Why this stone exists.** Stones 6–12 measured the BELIEF — calibration, gap from market, evidence grounding. None of them scored the action the agent actually took. Stone 13 puts the action layer on the scoreboard.

**The two-sided framing.** Two equally important sides, both graded the same way:

- Did the agent trade when the gap justified it?
- Did the agent decline to trade when the gap didn't?

Most evaluation systems get the second side wrong. They reward "good trades" and ignore "good restraint," which produces an agent that always finds a trade because trades are scored and restraint is invisible. That's the failure mode named in BIAS_PATTERNS #12 (trade-for-trade's-sake). Stone 13 fixes it by making `NoAction` a typed, first-class outcome that gets graded the same way `TradeAction` does.

**The three coherence checks.** For each Contract, the evaluator runs three mechanical checks on the action vs the inputs (belief, gap, costs) at decision time — no outcome needed:

| Check | What it verifies |
|---|---|
| Threshold match | Did the agent trade iff the gap on the truth-candidate state exceeded the cost threshold? (Trade if `gap > cost`. `NoAction` if `gap ≤ cost`.) |
| Direction match | If trading, is the position on the right side of the gap? (Positive gap on `strengthening` → long; negative gap → short.) |
| Expression match | If trading, does the expression type fit the belief shape? (Directional belief → equity-long/short. Bimodal belief → straddle. Concentrated uncertainty → vol-long. Pair structure → relative-value.) |

The action is **coherent** iff all three checks pass. Otherwise it's **incoherent**, and the specific sub-flag(s) that failed are stored alongside the verdict.

**Worked example — six Contracts on AAPL.** All 1-month horizon, three states `{strengthening, stable, decaying}`. Cost threshold = 5 pp (a trade needs gap > 5 pp on the truth-candidate state to overcome its round-trip costs):

| # | P_AI(strg) | P_mkt(strg) | Gap on strg | Rationality says | Agent's action | Verdict | Sub-flag failing |
|---|---:|---:|---:|---|---|---|---|
| A | 65% | 40% | +25 pp | Long equity | Long equity | ✓ coherent | — |
| B | 55% | 50% | +5 pp | NoAction (gap = cost) | Long equity | ✗ incoherent | threshold_miss |
| C | 35% | 45% | -10 pp | Short equity | Long equity | ✗ incoherent | direction_miss |
| D | 30% | 35% | -5 pp | NoAction | NoAction | ✓ coherent | — |
| E | 50% | 50% | 0 pp | NoAction | NoAction | ✓ coherent | — |
| F | bimodal {strg: 50%, stbl: 0%, dec: 50%} | flat market | 0 pp on strg | Straddle / vol-long | Long equity | ✗ incoherent | expression_miss |

Three of six coherent (A, D, E). Three incoherent (B, C, F) — each failing a different sub-flag, which is stored separately so the SOURCE of the incoherence is visible downstream.

**Per-agent aggregation.**

`decision_quality_rate` = coherent / total = **3/6 = 0.50** for this agent. Across agent types:

| Agent | Total | Coherent | Rate | Threshold-miss | Direction-miss | Expression-miss | Read |
|---|---:|---:|---:|---:|---:|---:|---|
| Discriminating | 50 | 47 | 0.94 | 1 | 1 | 1 | Trades when gap > cost, right side, right expression |
| Mixed (above) | 6 | 3 | 0.50 | 1 | 1 | 1 | Mixed failures across all three sub-flags |
| Trade-spammer | 100 | 35 | 0.35 | 45 | 15 | 5 | Trades below cost constantly; main failure mode is threshold |
| Lazy (always NoAction) | 100 | 60 | 0.60 | 0 | 0 | 0 | Coherent often (most situations call for NoAction) but never acts on real edge |

The trade-spammer's failure is concentrated in threshold-miss (trades when shouldn't). Discriminating agent's three misses are spread evenly — small sample of marginal cases. The lazy agent has clean Stone 13 numbers because they never make a wrong trade — they make NO trades.

**Stone 13 is a column, NOT a hard cap.** This is the load-bearing framing change from the original draft. Two compensating-virtue scenarios that prove a hard cap on `decision_quality_rate` would filter out skill:

- **The lazy agent looks better than they are on Stone 13 alone.** 60% coherence — coherent on most rows because most market situations DO call for NoAction. But they sit on every real edge. Stone 13 alone doesn't catch them. **Combine with Stone 11a (mean `belief_delta_on_truth`):** the lazy agent's mean gap is near-zero (they never act, so their actions structurally don't capture the gap), so Stone 11a marks them. The two columns together unmask them.
- **The sophisticated agent looks worse than they are on Stone 13 alone.** A real agent might legitimately deviate from the textbook coherent action: declining a positive-gap trade because the position is crowded, shorting a winner to lock in gain, using long-vol when implied vol is unusually cheap relative to belief structure. The three mechanical checks don't model these factors. A hard cap at 0.90 would filter out a 0.70-coherence agent whose other columns (gap, calibration, sizing) are strong — exactly the agent we want to promote.

So: `decision_quality_rate` is a column on the scoreboard. The promotion gate combines it with `belief_delta`, `unmotivated_update_rate`, held-out replay return, and Kelly-sizing quality using an explicit rule. No fixed threshold. See Stone 9's "column-on-scoreboard vs hard-cap-on-column" discussion for the general principle.

**Per-sub-flag aggregation (what the three columns reveal).** Storing the sub-flags separately lets the gate distinguish failure shapes:

- High threshold-miss rate → trade-for-trade's-sake agent. Trades below the cost threshold constantly.
- High direction-miss rate → agent's belief and action disagree about which side of the gap to take. Possibly a sign-error somewhere in the cognition.
- High expression-miss rate → agent reads the belief shape but picks the wrong instrument (e.g., directional trade on a bimodal belief). Pattern matches a model that hasn't internalized payoff structures.

Each sub-flag is its own diagnostic. They are NOT combined into the rate without the breakout; the breakout is what lets a promotion gate diagnose what's actually broken when coherence is low.

**What Stone 13 does NOT measure.**

- **Sizing.** "Should the long be size 5 or size 50?" — that's Kelly territory (Stone 33).
- **Capacity.** "Can the size actually be deployed at scale?" — Stone 14 (capacity-adjusted return).
- **Did the trade make money.** Outcome-grading is rejected (DESIGN.md #1, Stone 4). A coherent decision can lose; an incoherent decision can win. Stone 13 grades the decision, not the realized P&L.

**Connection to BIAS_PATTERNS #12.** Trade-for-trade's-sake is now structurally detectable: high threshold-miss rate. The pattern was named in BIAS_PATTERNS to be watched for; Stone 13's threshold-miss flag is the watcher.

**Connection to NoAction as first-class.** Cases D and E in the worked example both score coherent. Neither traded. They are NOT folded into a degenerate "size 0 trade" — they are scored as their own type of correct decision. From [CONTRACT.md](CONTRACT.md): `NoAction { decision_time, reason }` is a typed peer of `TradeAction`, with its own scoring path.

**One sentence.** Stone 13 grades the action's coherence with the inputs (belief, gap, costs) via three mechanical checks (threshold-match, direction-match, expression-match) with three sub-flags stored separately for diagnosis; the resulting `decision_quality_rate` is a scoreboard column the promotion gate weighs alongside other signals — NOT a hard cap — because sophisticated agents can legitimately deviate from the textbook coherent action and the gate needs to see the full picture to judge.

### Stone 14 — capacity-adjusted return

**Why this stone exists.** Stones 11a and 13 measured the gap in probability space — the difference between the agent's belief and the market's, and whether the agent acted coherently on it. Neither measured what fraction of that gap actually arrives in your account after you try to capture it. Stone 14 closes the loop between *nominal edge* (what you saw) and *realized edge* (what you got).

**The four frictions between nominal and realized.**

1. **Bid-ask spread.** Buy at the ask, sell at the bid. Lose half the spread on each leg of the round trip.
2. **Commission.** Fixed cost per trade. Mostly zero at retail brokers; not zero everywhere.
3. **Market impact.** Your buying pushes the price up; your selling pushes it down. Scales with your size relative to the market's normal daily volume.
4. **Alpha decay during execution.** If you can't fill in one print, you spread over multiple days. While you're filling, others see the same gap and the price drifts.

The first two are fixed. The third and fourth scale with size.

**The size-vs-liquidity relationship.** The empirical square-root law (Almgren and others): market impact grows with the square root of (size ÷ average daily volume). Double your size → impact grows by about 1.4×, not 2×. Take 10× the size → impact about 3× as bad. Deeper markets (higher ADV) hurt less per dollar of trade.

**Worked example — liquid name, AAPL.** Gap = +25 pp on strengthening. Agent goes long equity. AAPL ADV ~ $5B. Spread ~ 5 bps per side.

| Trade size | Size / ADV | Round-trip cost | Realized edge |
|---:|---:|---:|---:|
| $10,000 | 0.0002% | ~10 bps | ~24.9 pp |
| $1,000,000 | 0.02% | ~12 bps | ~24.9 pp |
| $100,000,000 | 2% | ~30 bps | ~24.7 pp |
| $1,000,000,000 | 20% | ~200 bps + multi-day execution | ~23 pp |

For AAPL, you need genuinely institutional size before capacity starts biting. Retail doesn't see the friction here.

**Worked example — less liquid name, microcap ABC.** Same gap (+25 pp), same direction. ABC ADV ~ $500K. Spread ~ 50 bps per side.

| Trade size | Size / ADV | Round-trip cost | Realized edge |
|---:|---:|---:|---:|
| $1,000 | 0.2% | ~100 bps | 24.0 pp |
| $10,000 | 2% | ~150 bps | 23.5 pp |
| $100,000 | 20% | ~500 bps + multi-day execution | ~20.0 pp |
| $1,000,000 | 200% | impossible without weeks of TWAP, alpha mostly gone | ~0–5 pp |

Same gap, same agent, different name. The microcap edge degrades fast as size scales.

**The discovered fact — capacity profile per agent.** Aggregating across many predictions reveals where each agent's edge actually lives:

| Agent | Mean nominal edge | At $10K | At $1M | At $100M |
|---|---:|---:|---:|---:|
| Liquid-name specialist | +10 pp | +9.9 pp | +9.7 pp | +9.0 pp |
| Microcap specialist | +30 pp | +29.5 pp | +15.0 pp | **−5 pp** |
| Mixed | +18 pp | +17.5 pp | +14.0 pp | +2.0 pp |

The microcap specialist looks dominant on nominal edge — until you try to put real money to work. At $100M the edge inverts; at $1M it's halved. The liquid-name specialist looks smaller per-trade but scales beautifully. **Stone 14 makes the capacity profile of each agent's edge visible** so the promotion decision can match the agent to the size range that matters.

**Per-agent aggregation.**

For each Contract: `realized_edge = nominal_edge − spread − commission − impact(size, ADV) − alpha_decay`. Then:

```
mean_realized_edge        = average of realized_edge across all Contracts
realized_to_nominal_ratio = mean_realized_edge / mean_nominal_edge
```

The ratio is the headline diagnostic. Near 1.0 = the agent's edge survives at their chosen sizes. Near 0.5 = half is eaten by friction. Below 0 = the agent's strategy actively loses money at their chosen size.

**Sliceable primarily by size bucket.** The most important slicing dimension for Stone 14 is **deployable size**, not horizon or sector. The scoreboard supports queries like `mean_realized_edge_at_size(agent, size_bucket)`. The promotion gate evaluates per-bucket, not just on the aggregate.

**Column, NOT a hard cap (per Stone 9's column-vs-cap meta-principle).** A high-realized-edge agent at $10K may be loss-making at $100M and vice versa. A single threshold can't capture this. The promotion gate sees the full size profile and decides.

**One near-tautological structural check.** Mean realized edge at the agent's stated deployable-size range must be **positive**. This isn't an arbitrary cap; it's what "having an edge" literally means. An agent whose realized edge is negative at the size they propose isn't an edge — it's a losing strategy. Different from the 0.90 I overproposed in Stone 13: this is a `> 0` constraint that's tautological, not a calibrated threshold.

**Connection to Stone 33 (Kelly sizing).** Stone 33 asks "was the agent's size Kelly-optimal given the gap?" Stone 14 asks "does the agent's stated size produce positive realized return after frictions?" Both can fail independently. An agent might pick the right Kelly fraction nominally (passes 33) but choose a microcap name where size × liquidity wipes the gap (fails 14).

**Connection to expression-type (Stone 11).** Different expressions have different capacity ceilings:

| Expression | Typical capacity |
|---|---|
| Equity-long in mega-cap | Very high |
| Equity-long in small/microcap | Low to medium |
| Options on liquid single names | Medium |
| Options on illiquid single names | Low |
| Pairs / relative-value | Medium |
| Vol-spreads | Medium to low |
| OTC structures | Low |

The promotion gate sees `realized_edge × expression_type × size_bucket` as a multi-dimensional slice. Skill is tagged per slice — same `domain_of_validity` logic as Stones 10 and 11.

**The cost-model dependency.** Stone 14 needs realistic models for spread, impact, and execution drag. Phase 0 toys use simple constructed models (fixed spread, square-root impact with calibrated constant). Phase 2+ refines from observed execution data. The deferred-fields list in [CONTRACT.md](CONTRACT.md) (cost_model, slippage_model, capacity_estimate, payoff_distribution) maps to Stone 14's inputs.

**What Stone 14 does NOT measure.**

- **Kelly optimality of size.** Stone 33's job. Stone 14 takes the size as given.
- **Whether the agent's belief was right.** Stones 6–8 / 11a / 13 do that. Stone 14 takes the gap as given.
- **Process quality of the update.** Stone 12's job.

It only measures: at the agent's stated size, what fraction of the nominal edge actually survives to the account?

**Connection to DESIGN.md.** Capacity-adjusted scoring is a stated DESIGN.md Operational Constraint — Phase 5 (year-2) requires "capacity-adjusted scoring with realistic retail market-impact assumptions" (Stone 44). Stone 14 is the scoreboard machinery; Stone 44 is the year-2 refinement using accumulated execution data.

**One sentence.** Stone 14 maps the agent's stated size against the underlying's liquidity (via spread, commission, square-root impact, and alpha decay) to compute realized edge — produces a per-Contract column and per-size-bucket aggregates so the promotion gate evaluates each agent's capacity profile rather than just their headline nominal edge, with one structural near-cap: realized edge at the agent's stated size must be positive, because anything else isn't edge.

---

**Layer 2 — the evaluator's math — complete.** Stones 8 through 14: calibration (8), scoreboard assembly (9), multi-horizon (10), expression-type tagging (11), market-delta scoring (11a), process-quality flag (12), decision-quality with NoAction as peer (13), capacity-adjusted return (14). The evaluator's full column set is now specified at the conceptual level. Implementation follows in Phase 0 substeps 4b/4c. Next: **Layer 3 — evaluator validated on toys** (synthetic-market toy, adversarial agents, validation, reliability diagrams, model interface contract, memory schema, property tests).

---

*Higher layers (2 through Apex) are itemized stone-by-stone in the table of contents at the top of this document. Detailed summaries land here as each stone is taught.*
