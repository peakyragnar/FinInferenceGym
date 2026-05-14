# Intuitions

This file records intuitions Michael is internalizing as the Financial Inference Gym is built layer by layer. It stays brief. Intuitions are conceptual, not technical. Math, code, and worked examples live elsewhere.

## 1. Belief Revision Under Evidence

Learning is revising a belief in response to evidence, in a way that makes future behavior better, where "better" is judged by something outside you. The atom of the entire gym.

- **Before evidence:** you have a belief (prior).
- **Evidence arrives:** an event with known likelihood under each hypothesis.
- **After evidence:** new belief = (prior × likelihood) ÷ (sum across all hypotheses).
- **Jump size:** controlled entirely by the ratio of likelihoods. Similar hypotheses → small jumps. Distinguishable hypotheses → big jumps.

The agent does not choose the update size. The math forces it. There is no learning rate, no calibration knob. This is the discipline of belief revision.

The danger: if your hypothesis space is wrong, or your likelihoods are wrong, the math will confidently produce the wrong answer. Never assign probability exactly 0 or 1 to anything you are not logically certain about — once a hypothesis is ruled out, no future evidence can resurrect it.

Toy artifact: [src/fingym/toys/coin.py](src/fingym/toys/coin.py).

## 2. Calibration Over Confidence

The agent produces probabilistic beliefs. The natural question — *"was the agent right?"* — is the wrong one. A confidently-wrong agent and an honestly-uncertain agent can both land on the correct side of a single call.

- **Calibration:** when the agent says X%, the truth is X% of the time.
- **Calibrated agent:** honest about what it knows. Says 70% when correct ~70% of the time.
- **Overconfident agent:** says 99% but is correct only 70% of the time. Sounds smart, structurally wrong, eventually blows up.
- **The correct test:** not *"did the bet land on the right side"* but *"does the agent's stated confidence match reality across many calls?"*

Scoring by outcome rewards confidence and produces overconfident agents. Scoring by calibration rewards honesty and produces inference-quality agents.

The gym scores the **belief**, not the outcome of the bet. Money-made measures luck, calibration, market noise, sizing, and timing all mashed together. Calibration measures the inference itself, in isolation.

### The scoring tool: Brier score

A scoring rule is the actual mechanism that turns a belief plus an outcome into a number. The simplest one that rewards honesty is the **Brier score**: take the probability the agent assigned to what actually happened, subtract from 1, and square it. Lower is better.

- Said 70% biased, truth was biased → loss = (1 − 0.70)² = 0.09 (small loss, mildly confident, correct)
- Said 99% biased, truth was biased → loss = (1 − 0.99)² = 0.0001 (tiny loss, confidently correct)
- Said 50% biased, truth was biased → loss = (1 − 0.50)² = 0.25 (medium loss, wishy-washy)
- Said 1% biased, truth was biased → loss = (1 − 0.01)² = 0.9801 (huge loss, confidently wrong)

The squaring is the trick. Confidently-wrong predictions are punished disproportionately more than mildly-wrong ones, so the only way to *average* a low loss across many calls is to report your true belief. That is what makes Brier a **proper scoring rule** — it makes honesty the dominant strategy.

### Scoreboard, not a single number

The evaluator produces a **scoreboard** — a vector of complementary metrics — not a single scalar. A single number can hide important failure modes (e.g., an agent that always says 50% is technically calibrated but useless).

- **Per-prediction scalar:** Brier (or log score) — useful for averaging and selection.
- **Complementary lenses the scoreboard tracks:** calibration, sharpness, discrimination, tail performance, cost of information.
- **Collapse to a scalar only at decision points** (e.g., promote a skill or not), and make the collapse rule explicit. Different decisions can use different collapses.

The same agent can look great under one lens and terrible under another. The evaluator's job is to expose that, not hide it.

## 3. The Hidden State Is the Real Object

The world has two layers:

- **State** — the real thing. Hidden. What you actually want to know.
- **Emissions** — what the state produces. Visible. Shadows of the state.

The agent only ever sees emissions. Its job is to infer the state from the shadows. The likelihoods are nothing more than the rule connecting state to emission.

- **In the coin:** state = which coin is in the box; emissions = each flip.
- **In finance:** state = is demand strengthening, is management honest, is the moat eroding; emissions = reported revenue, margins, transcripts, prices, options-implied moves.

The structure is identical. Revenue is not "the health of the business" — it is an emission *of* underlying health. Management's words are not "the truth about the company" — they are emissions filtered through incentive. A shallow agent confuses emissions for state and pattern-matches the shadows. A serious agent reads the same emissions and asks *which state would have produced these, with what likelihood?*

This is the alpha hypothesis of the entire gym: **markets price emissions. The opportunity lives in the gap between what the emissions look like and what the state actually is.**

The whole machinery: `hidden state → emission rules → observations → belief.`

Toy artifact: [src/fingym/toys/coin.py](src/fingym/toys/coin.py).

## 4. Time Grades the Agent

The agent forms a belief from the observations available **now**. The evaluator scores that belief against the label revealed **later**. The two never meet in the same moment.

- **Agent's information set:** strictly what is knowable by the as-of date.
- **Evaluator's information set:** the agent's information plus the future the agent could not yet see.
- **The asymmetry is the point.** It is what makes self-grading impossible and external evaluation real. The agent cannot inspect the answer key. Time reveals it.

This is the discipline behind **point-in-time replay**. Any leak of future information into the agent's present — a revised number, a restated fundamental, a transcript filed but timestamped earlier — turns the evaluator into a fake, because the agent is being graded on a future it covertly knew. The gym is only as honest as its time discipline.

A good gym treats time as a one-way valve. Information flows forward to the evaluator. It never flows backward to the agent.

## 5. Inference, Not Pattern Matching

Two ways for an agent to read emissions:

- **Pattern matcher:** looks for patterns *in* the emissions. Reads a strong-sounding quarter — revenue up, confident management — and outputs "good company." Operates on surfaces.
- **Inference agent:** asks *which state would have produced these emissions, with what likelihood?* Reads the same strong-sounding quarter and asks what underlying state most plausibly generated this set of emissions, given everything else visible. Operates on the latent layer.

The two look identical when emissions are clean and unambiguous. They diverge sharply when emissions are mixed: a confident transcript with rising receivables and a quiet options market. A pattern matcher sees three signals and averages. An inference agent asks which single hidden state would have produced all three.

Pattern matching is the default behavior of any system trained on emission-level data. It is also the failure mode of most "AI for finance" attempts: the model learns the surface and confuses the surface for the truth. The gym exists to force the harder mode.

The gym is not a feature-prediction system. It is a state-inference system.

## 6. Markets Price Emissions; Alpha Lives in the Gap

Markets do not price hidden states. They cannot — nobody can see the state. Markets price **emissions**: reported numbers, transcript tone, observable behavior, prior price action. The market's belief about the underlying state is *implicit*, recovered only by inverting what is priced into the emissions.

This is the alpha hypothesis of the gym:

- **You** form a belief about the hidden state from emissions.
- **The market** has also formed a belief about the hidden state, embedded in price.
- **The opportunity** is the gap between your belief and the market's, when you have evidence the market is misreading.

When the emissions look strong but the underlying state is weakening, the market (pricing the emissions) will over-pay. When the emissions look weak but the state is strengthening, the market will under-pay. The bet is never on the emissions directly. The bet is on the **gap between the state and the emission-priced consensus**.

Two consequences:

- A correct view that matches the market is not alpha. It is consensus.
- A view that disagrees with the market is only valuable if the disagreement is calibrated and the gap is large enough to survive costs and noise.

The gym's job is to surface and score those gaps. Not to identify "good companies." To identify mispriced state.

## 7. Calibrate the Evaluator in a Toy First

The coin is the only place where the hidden state is **verifiable**. We set the coin to biased, so we can grade any agent's belief against ground truth.

In finance, the state is never observable with certainty, even after the fact. You can only observe future emissions and treat them as proxies:

- *"Did demand actually weaken?"* → next-quarter revenue.
- *"Was management lying?"* → guide-down rate or future restatements.
- *"Was the moat eroding?"* → market-share trend over years.

Each proxy is itself a hypothesis about what the true state would have emitted. Proxies are not labels. They are best-effort substitutes for an unobtainable truth.

This is why every layer of the gym must be calibrated in toy worlds first. If your evaluator cannot score inference correctly when the state is known, you have no reason to trust it when the state is only inferred. **A scoring rule that fails in the coin world will fail silently in the real world.**

The toy is not training wheels. It is the audit. It is the only place where the auditor (you) can verify that the evaluator actually measures what it claims to measure.

## 8. Action Under Belief

A belief without an action is just a number on a screen. The gym is a decision machine. The agent must do something with what it knows.

- **Smallest action space:** COMMIT(hypothesis A), COMMIT(hypothesis B), or NO-EDGE (decline to commit).
- **Decision rule:** for each action, compute expected value under the current belief and the payoff structure. Take the action with highest EV.
- **Default action:** NO-EDGE has zero expected loss in every state. It is the action of first resort, not last resort.

Asymmetric payoffs change the threshold. The same 70% belief can be a strong buy with symmetric payoffs and a stand-aside with a 5× downside cost. **The decision is a function of belief and payoff structure together, never belief alone.**

Choosing not to bet is itself a decision. It requires the same calibration discipline as betting. In real markets, most opportunities are not edges — the well-calibrated agent's most-used action is NO-EDGE. Overconfident agents say it too rarely. Underconfident agents say it too often.

This is where calibration (Intuition 2) becomes load-bearing for money, not just for honesty. An overconfident agent doing EV math on inflated probabilities will systematically over-act. The decision rule is only as good as the belief feeding it.

The complete agent loop: observe emissions → update belief → compute EV of each action → act → be scored later.

## 9. Costly Observation

Free observations let the agent reach certainty for free. Real worlds have no free observations — every emission costs dollars, time, attention, or opportunity. The instant observations are priced, the agent must decide whether the next one is worth buying.

- **Core insight:** an observation is worth what it might change in your **action**, not what it changes in your **belief**. A shift from 70% to 75% that leaves the action unchanged is worthless. A shift from 51% to 49% that flips COMMIT to NO-EDGE is enormously valuable.
- **Diminishing returns:** the more certain the agent is, the less the next observation can move it across any decision threshold. Cost stays constant. Eventually `VoI < cost`.
- **The rule:** buy the next observation only if `VoI > cost`. Otherwise commit.

VoI is honest only when the belief feeding it is calibrated (Intuition 2). It is also a stop rule and a research-discipline rule at the same time: **research only where research might change the bet.**

In finance this is the discipline behind "what should I dig into." Reading is not free. Most analysts spend too much time on names where another hour of work won't change the call. The no-edge decision should arrive sooner than feels comfortable — as soon as no further observation is worth its cost.

NO-EDGE now becomes structurally cheap: the natural endpoint of a process where no more information is worth buying and no commit has positive EV. It is the disciplined call, not a cop-out.

## 10. Which Information to Buy

When multiple kinds of observations are available, each with its own cost and informativeness, the agent's decision is no longer "buy or stop" — it is **which one to buy**. This is the classical **bandit** problem: each kind of observation is an "arm."

- **Decision rule:** for each arm, compute VoI given current belief, divide by cost, pick the arm with highest VoI per dollar. Stop when no arm has positive VoI net of cost.
- **Informativeness is conditional.** An arm's VoI depends on which hypotheses the agent is currently trying to distinguish. The right source depends on what you're trying to figure out, and shifts as belief sharpens.
- **Independence matters.** Two sources that echo each other are not two sources. VoI math implicitly assumes independence; correlated sources are double-priced for one signal.
- **The contextual angle.** The best arm is a function of *context*. The right source for a semiconductor company is not the right source for software. Generic "always read transcripts" is not a strategy.

A **source diet** is the policy that selects which sources to consume for which kinds of cases. The gym compares diets head-to-head and rewards the one that produced the most **decision-changing information per dollar** — not the most information per dollar.

This is the seed of source-diet tournaments (AGENTS.md layer 11) and the operating definition of "what should I research" in finance: not "read everything," but **read what could change the call.**

## 11. The Market Is a Second Believer

The agent is never alone in finance. The market itself has a belief about the hidden state, and that belief is what generates the price on the screen.

> **Price is not an emission of the state. Price is an emission of the market's belief about the state.**

This is the most important reframe in finance. A stock trading at $100 is not "worth $100." It is what the market currently believes it is worth, given its current view of the underlying state. If the market's belief is wrong, the price is wrong.

### Inverting price to recover the market's belief

Since price embeds the market's belief, you can run inference in reverse: *given the price, what belief about the state would the market have to hold to produce it?* This is the most powerful tool in the gym. **The market's belief is not hidden. It is written in price-language and can be decoded.**

Three canonical inversions:

- **Implied DCF** — solve for the revenue growth, margins, or discount rate that justifies the current price. The market's implied forecast of fundamentals, recovered from price.
- **Options-implied probabilities** — extract a distribution of future price moves from option prices. The market's implied belief about volatility and tail risk.
- **Implied volatility** — a scalar compression of how uncertain the market is about future state.

### Edge is calibrated disagreement that clears costs

Once you have your belief and the market's belief, three conditions must all hold for a real trade:

1. **You disagree with the market.**
2. **You're calibrated** — your stated confidence matches your actual hit rate.
3. **The gap is large enough to survive costs, slippage, and the time you'll wait to be proven right.**

If any one fails, edge is zero or negative in expectation, regardless of how confident the agent feels. Consensus (you agree with the market) has no payoff even when both are right. Disagreement without calibration is luck. Disagreement with calibration but no margin is unprofitable certainty.

### The reframe this forces on the agent

Stop asking: *"Is this company good?"* — the market has already answered.
Start asking: *"Does the market accurately reflect what I think this company's hidden state is?"*

The opportunity lives in the gap, not in the view. A great company at a price that already reflects its greatness is a no-edge. A struggling company at a price that already reflects its struggling is a no-edge. Alpha is the residual after the market's belief is subtracted from yours.

The agent's source diet must include **market emissions** — price, options chain, implied vol — alongside fundamentals and transcripts. These are the market's broadcasts about its own belief, and they are the most distilled, lowest-latency emission the agent can read.

## 12. Sizing the Bet

A correctly identified edge can still ruin you if sized wrong. Sizing is a first-class decision, not a footnote to the bet.

- **The naive answer is wrong.** Maximizing expected value per bet is correct for one-shot bets and catastrophic for repeated bets. A positive-EV strategy sized at 100% of bankroll goes to zero with probability approaching 1.
- **Asymmetry of ruin.** Losses and gains do not cancel in compounding. A 50% loss requires a 100% gain to recover. A 100% loss is game over. EV math does not see this asymmetry — only compound math does.
- **Kelly fraction.** Bet a fraction of bankroll proportional to your edge, scaled down by the variance of the outcome. Kelly maximizes long-run compound growth rate, not single-bet EV. It is the unique size that balances "earn the edge" against "don't blow up."
- **Fractional Kelly.** Full Kelly assumes you know your edge exactly. You don't. You estimate it. Even small overestimates of edge cause full Kelly to overbet and risk ruin. Bet half-Kelly or quarter-Kelly to absorb miscalibration. Most professional traders run between 0.25× and 0.5× Kelly.

Sizing makes calibration (Intuition 2) load-bearing for money. Overconfidence about edge → overbetting → ruin. The honest agent assumes its belief is somewhat wrong and sizes for the worst plausible case.

Correlated bets share variance. Sizing each independent edge at Kelly overconcentrates risk on hidden common factors — a market regime, a macro variable. The gym must price correlation, not just count edges.

P&L without process is luck. Process without P&L is theater. **Both must be scored in parallel.** A single P&L number cannot tell you whether you have an agent or a coin flipper.

## 13. Time and the Two Ways to Be Wrong

Even a calibrated edge can lose money for quarters or years before converging. The gap between price-implied belief and true state can persist. The agent must continually answer one question while losing money:

> Is the thesis wrong, or is the market just slow?

- **Wrong on timing.** Belief about state is correct; the market hasn't updated yet. Hold, possibly add.
- **Wrong on thesis.** Belief was wrong; new emissions contradict it. Close.

These look identical day-to-day and demand opposite responses. The rule for telling them apart: **update on emissions, not on price.** A new emission that contradicts the hypothesis should lower the posterior. A price move against you with no new emission should not. Pattern matchers (Intuition 5) fail here because they read price as if it were evidence about state — when in fact price is the market's belief moving, which is precisely the gap they were betting on. **You cannot bet against the market and use it as your information source.**

Time itself is a cost in four ways: opportunity cost, carrying cost, psychological cost, and information decay (the world drifts away from the conditions in which your belief was formed). "I'll just wait" is never free.

Sizing (Intuition 12) and time are linked. Full Kelly cannot survive a long correct divergence. Fractional Kelly absorbs miscalibration of *time* the same way it absorbs miscalibration of *edge* — the agent that thinks "this converges in 6 months" and is wrong by 3× must still be alive when it does.

The evaluator must score not just P&L but **process across time**: did the agent update on new emissions or on price alone, did it close on broken thesis vs. hold on slow timing, did its stated confidence track its actual hit rate over the life of the position. A correctly-held timing trade that eventually paid off looks identical in P&L to a wrong-thesis trade that got lucky. The process scoreboard must distinguish them.

## 14. Reflexivity: Your Own Trades Are Emissions

When the agent is small, the market produces emissions and the agent observes them. When the agent is large enough to matter, **the agent's own trades become emissions** other participants observe and update on. Price is no longer a pure observation of state — it is partly the agent moving prices and partly the market reacting to that movement.

Two flavors:

- **Mechanical impact (slippage).** Buying pushes price up, selling pushes it down. Scales with position size relative to liquidity.
- **Belief impact.** Other participants observe your activity and update their beliefs. The market's belief about state shifts *because of your trades*, not because new information about the state appeared.

For every real edge there is a **capacity curve** — how much can be deployed before the edge converges to zero. Past the threshold, deploying more capital makes *less* money, not more. This is the most counterintuitive fact in finance.

Naive backtests lie about capacity. Historical prices were what they were *given the trades that actually happened*. Replaying with realistic market-impact assumptions vaporizes most apparent edges. The gym must score **deployable edge at intended size**, not nominal edge at zero size. A 3% edge with $5B capacity dominates a 20% edge with $5M capacity once size is honestly priced.

The deepest version is **Soros-style reflexivity**: the agent's trades change the *hidden state itself*, not just the market's belief about it. Buying enough lowers a company's cost of capital and the business genuinely strengthens. Short-selling enough starves a company and it weakens. The inference chain (Intuition 3) gets corrupted — emissions are no longer purely a function of an exogenous state, because the state is being moved by the inference process.

The scorecard must include edge at deployable size, capacity, crowding sensitivity, and a reflexivity flag (does the trade move the state itself).

> **Know not just what your edge is, but the size at which it stops being an edge.**
