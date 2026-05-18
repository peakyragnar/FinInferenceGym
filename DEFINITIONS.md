# Definitions

Glossary of core vocabulary for the Financial Inference Gym. Definitions are short, operational, and tied to how the gym will work. Math and worked examples live elsewhere. Entries are alphabetical.

This file grows as teaching proceeds. New v5 vocabulary (Forecast Ledger, Signal Class, Signal-Class Reliability, Tradable Edge, Calibrated Expected Utility, Market-State Baseline, Track A, Track C, Incremental AI Edge, Realized Edge, Forecast Edge, etc.) lands here as the corresponding PYRAMID stones are taught and distilled (the cadence used throughout Phase 0).

## Action space

The set of actions available to the agent at decision time. The smallest non-trivial action space contains one **COMMIT** action per hypothesis plus a **NO-EDGE** action that declines to commit, with **OBSERVE_AGAIN** as an auxiliary action that buys more evidence before committing.

In the coin toy:

```text
{ COMMIT(biased), COMMIT(fair), NO-EDGE }    plus  OBSERVE_AGAIN
```

Every richer setup — sized bets, options expressions, hedge ratios, portfolios — is a refinement of this minimal space.

## Asymmetry of ruin

The fact that losses and gains do not cancel in compound returns. A 50% drawdown requires a 100% gain to recover; a 100% loss cannot be recovered at any subsequent gain. Compound math sees this asymmetry; single-bet expected-value math does not. The asymmetry is what makes sizing non-trivial: any strategy that ignores it will eventually go to zero, regardless of how positive its per-bet EV.

## Bandit

A decision problem where the agent must repeatedly choose between multiple "arms," each of which has its own cost and reveals a signal. The agent's task is to allocate a budget across arms to maximize decision-relevant information per dollar. In the gym, each kind of observation (transcript, options data, peer behavior, etc.) is an arm.

## Belief

A probability distribution over hypotheses. Not a guess. Not a point estimate. A weighted distribution that sums to 1. Under v5, the agent's belief at decision time is a **forecast distribution over realized returns** (see `Contract`).

## Calibrated forecast (`F_AI_calibrated`)

The agent's raw forecast distribution `F_AI` after shrinkage toward per-signal-class empirical reliability from the Forecast Ledger. Same shape as `F_AI` (probability distribution over realized return buckets; sums to 1; no zeros — Cromwell holds). Computed by the Tradable-Edge Action Engine at decision time, not by the agent. Stored on the Contract as the `calibrated_forecast` field. Used as the input to calibrated expected utility computation and the margin-of-safety action gate. **The verifier-side calibrated version of the agent's cognition.**

## Brier score

A proper scoring rule for probabilistic predictions. For each prediction, take the probability the agent assigned to the outcome that actually happened, subtract from 1, and square it. Lower is better. The squaring punishes confidently-wrong predictions disproportionately more than mildly-wrong ones, which is what makes lying about confidence cost more, on average, than honesty.

## Calibration

The property that, when the agent says X%, the truth occurs X% of the time across many such calls. A 70%-calibrated agent is honest about what it knows. An overconfident agent (says 99%, right only 70%) is structurally wrong even when individual calls land correctly. Under v5, calibration is measured empirically per signal class via the Forecast Ledger (v5 vocabulary to be defined when its PYRAMID stone is taught).

## Capacity

The maximum size at which a strategy can be deployed before its edge converges to zero. For any real edge there is a capacity curve: small size captures the full edge, medium size captures partial edge after slippage, large size captures none because market impact moves the price to consensus. Past the capacity threshold, deploying more capital makes less money, not more. The gym must score edge at deployable size, not nominal edge at zero impact.

## Contextual bandit

A bandit problem where the optimal arm depends on **context** — the specific case in front of the agent. The right source for a semiconductor company differs from a software company. The agent must learn not just "which arm is best on average" but "which arm is best given **this** case."

## Contract

The structured terminal output an agent emits at decision time. A `Contract` is the typed object that turns unconstrained model cognition into a scoreable, time-separated, calibration-ready claim. Every cognitive output the system takes seriously must take this form. The MVP spec is in [CONTRACT.md](CONTRACT.md). Cognition fields are populated by the agent (AI Core); verification fields are populated by the Tradable-Edge Action Engine. A model output that does not land in a `Contract` is prose, not alpha — see [BIAS_PATTERNS.md](BIAS_PATTERNS.md) #11 (narrative as evidence).

## Emission

An observable produced by some underlying world process — earnings releases, transcripts, regulatory filings, fundamental disclosures, prices, headline observables (rates / realized + implied vol / FX / commodities). The agent reads emissions; the process producing them is not directly observed. Inference is the act of forming a forecast over the future given the emissions seen so far.

## Evaluator

The external judge that scores the agent's forecasts against realized returns using proper scoring rules. The agent proposes. The evaluator disposes. Never let the agent score itself.

## Expected value (EV)

The probability-weighted average of payoffs across outcomes for a given action. With current forecast `F` and payoff structure `V`:

```text
EV(action) = sum over outcomes of F(outcome) × V(action, outcome)
```

The decision rule is: take the action with the highest EV. EV is only honest when the forecast feeding it is calibrated — an overconfident agent doing EV math on inflated probabilities will systematically over-act. Under v5, the Tradable-Edge Action Engine computes EV under the **calibration-shrunk** forecast, not under the agent's raw forecast.

## Forecast distribution (`F_AI`)

The agent's probability distribution over buckets of `R_realized` for a specific (name, horizon, expression-type). Emitted by the AI Core at decision time alongside a `signal_class_id` tag. Sums to 1; no bucket is assigned 0 (Cromwell). Stored on the Contract as the `forecast_distribution` field. **The cognition-side output of the AI Core under Constitution v5** — replaces the pre-v5 belief distribution over hidden states.

## Fractional Kelly

A practical version of the Kelly fraction that bets a multiple less than 1.0 (e.g., 0.5× Kelly, 0.25× Kelly) to absorb miscalibration of the agent's stated edge. Full Kelly assumes the edge is known exactly; in practice it is estimated. Even small overestimates lead full Kelly to overbet and risk ruin. Most professional traders run between 0.25× and 0.5× Kelly.

## Hypothesis

A candidate value or bucket the agent entertains as possibly true. The agent never sees which hypothesis is correct — it only sees observations, and assigns belief across the hypothesis space. Under v5, the hypothesis space is the support of the agent's forecast distribution over realized returns.

## Inference chain

The structural loop the gym is built around:

```text
emissions → forecast distribution over realized returns
```

The agent observes emissions and produces a forecast distribution. The forecast is then shrunk toward per-signal-class empirical reliability (verifier-side calibration step), and the action gate operates on the shrunk forecast. Every layer of the gym sits inside this chain. (Pre-v5 framing — "hidden state → emission rules → observations → belief" — was retired by Constitution v5.)

## Kelly fraction

The fraction of bankroll that maximizes long-run compound growth rate for a given edge and outcome variance. In words: bet a fraction proportional to your edge, scaled down by how volatile the outcome is. Kelly is the unique size that earns the most compound growth without certain ruin. Bet larger than Kelly: growth falls and ruin probability rises. Bet smaller: growth falls but ruin probability is low. Optimizing Kelly is fundamentally different from maximizing single-bet expected value.

## Label

The future truth or outcome the evaluator uses to score the agent. The agent does not see the label when making its prediction. Only the evaluator sees it later. Under v5, the label is the **realized return** at horizon for the `(name, horizon, expression-type)` the forecast applies to.

```text
observation = evidence available then
label       = realized return revealed later
```

If observations are treated as labels, the gym becomes fake.

## Likelihood

How often a given hypothesis would produce the observation that was just seen, if that hypothesis were true. A property of the world, not the agent. Likelihoods do not depend on the agent's belief.

## Market impact

The price move caused by the agent's own trading activity. Buying pushes price up; selling pushes it down. Scales with position size relative to market liquidity. Closely related to **slippage** — the difference between the price the agent intended to trade at and the price it actually got. Any honest evaluator must price market impact at the size the strategy is intended to run.

## No-edge

The action of declining to commit to any forecast-driven trade. Zero expected payoff, zero expected loss, in every state. The correct default when no commit-action has positive calibrated expected utility after the margin-of-safety threshold. In real markets, the well-calibrated agent's most-used action. Overconfident agents say it too rarely; underconfident agents say it too often. NO-EDGE is a **first-class output** in the system (DESIGN.md Operational Constraints) — the verifier explicitly rewards it when correct. A `Contract` whose `final_action` carries `NoAction` is structurally equivalent to one carrying `TradeAction`; both are scored, both can be promoted into memory, and both contribute to the trajectory store.

## NoEdgeContract

Informal name for a `Contract` whose `final_action` is `NoAction`. Carries the same required fields as a trade-bearing `Contract` (forecast distribution, signal class, falsifiers, realized return plan, cognitive audit trail) — declining to trade is itself a typed claim that gets scored. Did the no-edge call hold up? Was the margin-of-safety gate's verdict correct? The `NoEdgeContract` is the verifier's defense against trade-for-trade's-sake (BIAS_PATTERNS.md #12).

## Observation

Information available to the agent at the time it must form a forecast. Evidence, not truth. Can be useful, misleading, incomplete, delayed, or contaminated by consensus.

## Payoff structure

The matrix of rewards and losses for each (action, outcome) pair. The same forecast can imply different decisions under different payoff structures — a 70% confidence can be a strong commit under symmetric payoffs and a stand-aside under asymmetric downside. **Decisions depend on forecast and payoff structure together, never forecast alone.**

## Point-in-time

A discipline in which the agent's information set is strictly limited to what was knowable at a specific as-of date. Restated, revised, or retroactively-dated data is excluded. Without point-in-time discipline, the evaluator is fake: the agent is being graded on a future it covertly knew. Information flows forward to the evaluator; it never flows backward to the agent.

## Posterior

The agent's belief over its hypotheses *after* the observation has been incorporated. Computed from prior and likelihood. Becomes the prior for the next step.

## Price

An observable market emission. Under v5, used by the Market-State Baseline (Track C) as a headline observable and by the realized-return labelling function (the realized return at horizon is computed from price + corporate actions + payoff structure). The AI Core consumes the same raw prices the Baseline does. Neither the agent nor the Action Engine inverts price to recover a market belief over hidden state — that pre-v5 mechanism was removed by Constitution v5; calibration is now empirical, via the Forecast Ledger.

## Prior

The agent's belief over its hypotheses *before* any new evidence arrives. Whatever the previous step left behind, or — at the start — a default.

## Proper scoring rule

A scoring rule with the property that, on average, the way to maximize your score is to report your true belief. Lying — inflating confidence or hedging — costs you more than honesty does. Brier score and log score are the canonical proper scoring rules.

## Realized volatility

The standard deviation of past price returns over a specified window. A statistic computed from past emissions. Used as one of the Market-State Baseline's headline observable inputs.

## Realized return (`R_realized`)

The actual log return for a (name, horizon, expression-type) over the period from decision time to horizon. Revealed at the horizon by the labelling function (which takes future price + corporate actions + payoff structure → realized log return). Not known at decision time. **The grading object for forecasts under Constitution v5** — replaces "hidden state" as the predicted object. The `realized_returns` Postgres table holds one row per resolved (Contract, horizon) pair.

## Reflexivity

The phenomenon by which the agent's own activity becomes part of the market's information environment — and, in strong forms, part of the world process being forecast. Two flavors:

- **Mechanical impact** — slippage that degrades the price at which the agent can execute.
- **Belief impact** — other participants observe the agent's trades and update accordingly.

The strongest form is **Soros-style reflexivity**, where the act of trading changes the underlying business or system: buying enough of a stock lowers the company's cost of capital and improves its fundamentals; short-selling enough starves it and weakens it. Reflexivity corrupts the inference chain by making the world process non-independent of the agents forecasting it.

## Shape of the gym

Every primitive in the gym sits inside one frame:

- **Costly observation** → buy more emissions to refine your forecast.
- **Source diets** → which emissions are most informative about realized returns?
- **Forecast + empirical calibration** → produce a forecast distribution over realized returns; the verifier shrinks it toward per-signal-class empirical reliability.
- **Margin-of-safety action gate / no-edge** → act only when calibrated expected utility clears a threshold; otherwise NoAction.
- **Isolated Market-State Baseline** → a parallel control on headline observables, used for incremental-AI-edge attribution.

The unifying form: **forecast the future from the shadows, empirically calibrate the forecast, and act only when the gate clears — then audit what edge came from the AI vs from headline observables anyone has.**

## Signal class

The agent's own categorization tag for "what kind of forecast this is." Stored on the Contract as the `signal_class_id` field. Examples: `mid_cap_tech_margin_surprise_q3`, `commodity_supply_shock_3m_equity_long`, `cfo_qualifier_density_q3_post_2020` (the last has no Wall Street analog — the agent invents categorizations as it discovers them).

**The agent proposes; the Forecast Ledger tracks per-signal-class empirical reliability over many forecasts.** At decision time, the Action Engine looks up reliability for the signal class and shrinks the agent's raw `F_AI` toward the empirical rate — producing `F_AI_calibrated`. Signal classes can be broad (more samples, statistically firm, less discriminating) or narrow (fewer samples, more discriminating; aggressive shrinkage applies). Signal classes are **searchable** (per DESIGN.md "Searchable vs Architectural") — they evolve as the agent discovers what works; the architecture doesn't pre-define them.

## Source diet

The policy that selects which sources (arms) the agent consumes for which kinds of cases. A strategic choice: broad and expensive vs. narrow and risky vs. adaptive to context. The gym compares diets head-to-head by running them against the same historical episodes and scoring on calibration and net-of-cost reward. The winning diet is the one that produces the most decision-changing information per dollar.

## Thesis vs timing

The two distinct failure modes a losing position can exhibit:

- **Wrong on timing** — the forecast was correct; the market has not yet moved. Right action: hold or add.
- **Wrong on thesis** — the forecast was wrong; new emissions contradict it. Right action: close.

They look identical in P&L day-to-day and demand opposite responses. The rule for telling them apart: **update on emissions, not on price.** A new emission inconsistent with the forecast lowers the posterior; a price move with no new emission does not.

## Time costs

The four costs of holding a position over time, all of which must be priced by an honest evaluator:

- **Opportunity cost** — capital tied up is unavailable for other edges.
- **Carrying cost** — direct cost of holding (futures, options, levered positions).
- **Psychological cost** — long drawdowns erode discipline and cause closing at the wrong moment.
- **Information decay** — the world drifts; conditions under which the forecast was formed may no longer hold.

"I'll just wait" is not a free action.

## Value of information (VoI)

The expected change in the agent's best-action EV after seeing a potential observation, computed before paying for it. The decision rule is: buy the observation if `VoI > cost`; otherwise commit. VoI counts only belief changes that **cross a decision threshold** — belief shifts that leave the action unchanged are worth zero. Serves simultaneously as a stop rule (stop observing when no observation has positive VoI net of cost) and a research-discipline rule (research only where research might change the bet). Honest only when the forecast feeding it is calibrated.
