# Financial Inference Gym — Canonical Design Document v0.1

## 0. One-sentence purpose

Build a partially observable financial inference gym where hidden cash-flow and market-belief states emit structured data, text signals, prices, and options surfaces; agents compete to infer future world distributions, identify gaps between their posterior and the market-implied posterior, and express those gaps as asymmetric bet cards.

## 1. What this is not

This is not a Wall Street analyst workflow accelerator.

This is not a chatbot that reads public information and produces stock pitches.

This is not an attempt to simulate the entire economy.

This is not an autonomous live-trading system.

This is not a synthetic-news generator whose fake articles are treated as truth.

This is not a generic RL project detached from finance.

## 2. Core thesis

Alpha is not expected to come from summarizing readily available information. The gym exists to train and evaluate agents on a harder problem: identifying which future economic states are underpriced or overpriced by the current market-implied distribution.

The goal is to learn better representations of the inference problem:

- What hidden state is this company likely in?
- What does the current market price imply investors believe?
- Which observations would most reduce uncertainty?
- Which future worlds are cheap or expensive relative to market odds?
- Is there an asymmetric expression after costs, liquidity, timing, and uncertainty?

## 3. Core mental model

At each company-time episode:

```text
hidden_state z_t
  → emits observations o_t
  → market forms belief m_t
  → market price p_t reflects m_t plus liquidity/flow/narrative distortion
  → agent forms belief q_t from a controlled source diet
  → agent chooses action a_t
  → environment advances
  → evaluator scores forecast, calibration, payoff, and reasoning quality
```

The opportunity is not `q_t says stock up`. The opportunity is:

```text
agent_posterior q_t differs from market-implied posterior m_t
AND the difference is expressible with favorable payoff after costs.
```

## 4. Key objects

### 4.1 Hidden state

The hidden state is not directly visible to the agent. It contains compact economic variables such as:

```text
demand_state
pricing_power_state
margin_pressure_state
inventory_state
balance_sheet_fragility
refinancing_risk
competitive_pressure
terminal_economics
management_credibility
market_attention
narrative_state
liquidity_pressure
crowding_state
```

### 4.2 Observations

Observations are what the agent is allowed to see under a source diet.

Observation types:

```text
fundamentals
prices
returns
volume
options surface
macro data
sector data
transcripts
filings
news
peer commentary
alternative data when available
```

Text observations may appear as raw text, extracted features, or synthetic emissions. Historical replay should use real text. Synthetic environments should begin with text-derived feature emissions before generating full synthetic text.

### 4.3 Source diet

A source diet is a controlled information-access policy.

Examples:

```text
price_only
fundamentals_only
transcripts_only
transcripts_plus_macro
options_only
fundamentals_plus_transcripts_no_price
full_context
full_context_ex_news
anti_consensus
```

The purpose is to test which forms of blindness or source restriction improve inference and reduce consensus contamination.

### 4.4 Market belief

The market belief is the distribution implied by the current price and options surface, distorted by flows, liquidity, attention, narrative, and institutional constraints.

The system should invert market price into assumptions:

```text
implied revenue CAGR
implied margin path
implied terminal growth
implied WACC / discount rate
implied impairment probability
implied event probability
implied volatility / move
```

### 4.5 Agent belief

The agent belief is the agent's posterior over hidden states and future worlds after seeing its source diet.

The agent must output distributions, not merely labels.

### 4.6 Bet card

The agent action is a structured bet card:

```yaml
ticker: string
as_of_date: date
source_diet: list[string]
direction: long | short | neutral | no_trade | option_structure
horizon: 1m | 3m | 6m | 12m
expected_return_distribution:
  p05: float
  p25: float
  p50: float
  p75: float
  p95: float
left_tail_probability: float
right_tail_probability: float
confidence: float
market_implied_assumptions: dict
agent_implied_assumptions: dict
reason_for_gap: string
best_expression: string
position_size: float
costs_considered: list[string]
kill_criteria: list[string]
disconfirming_evidence_to_seek: list[string]
expected_failure_mode: string
```

## 5. Environment versions

### v0 — toy hidden-state inference

Synthetic one-company environment with a small hidden state:

```text
healthy | demand_weakening | margin_pressure | refinancing_stress
```

Observations are noisy numeric and text-feature emissions.

Goal: learn the structure of hidden state, observation, action, reward.

### v1 — historical replay, structured only

Use actual historical prices, fundamentals, macro, and outcomes.

Agent sees only information available as of the replay date.

Goal: establish point-in-time evaluator discipline.

### v2 — historical replay with transcript features

Add real earnings transcripts and extracted transcript features:

```text
demand_softness_score
sales_cycle_elongation_score
management_evasiveness_score
analyst_pressure_score
pricing_power_score
inventory_pressure_score
guidance_specificity_score
```

Goal: test whether text features improve future-state inference.

### v3 — source-diet tournaments

Run agents with different information access over the same episodes.

Goal: identify which source diets work by regime, sector, and task.

### v4 — AlphaEvolve-style feature and rule discovery

Use an evolutionary loop to mutate candidate artifacts:

```text
feature formulas
transcript extractors
source diets
market-belief inversion models
DCF assumptions
trade-expression rules
kill criteria
reward weights
```

Goal: discover better representations and rules under a hard evaluator.

### v5 — sequential information-acquisition RL

The agent can choose what to inspect, paying costs:

```text
inspect_fundamentals
inspect_transcript
inspect_options_surface
inspect_macro
inspect_peer_transcripts
inspect_news
invert_market_price
submit_bet_card
submit_no_edge
```

Goal: learn sequential behavior: what to inspect, when to stop, when to trade, when to say no edge.

### v6 — synthetic worldlet model

Build narrow synthetic worldlets, not a full economy:

```text
enterprise_software_guide_down
industrial_margin_inflection
consumer_demand_break
refinancing_cliff
inventory_cycle_reversal
long_duration_rates_shock
options_underpriced_event
```

Goal: train robustness and counterfactual reasoning while anchoring validation in historical replay.

## 6. Reward design

Do not reward only P&L.

Reward components:

```text
cash_flow_forecast_accuracy
future_fundamental_state_accuracy
valuation_distribution_calibration
return_distribution_calibration
tail_event_detection
market_implied_assumption_inversion_accuracy
realized_trade_utility_after_costs
asymmetry_capture
correct_no_trade_decisions
```

Penalties:

```text
overconfidence
excessive complexity
unnecessary information cost
transaction costs
slippage / illiquidity
crowding / correlation
consensus copying
backtest overfit risk
wrong-reason profitable trades
```

A profitable trade with bad reasoning should receive less reward than a profitable trade whose predicted failure/success path matches the realized path.

## 7. AlphaEvolve role

AlphaEvolve-style search is for artifact discovery, not for running the whole agent.

Candidate artifacts:

```text
transcript feature formulas
DCF model components
market-implied inversion functions
source-diet policies
mispricing templates
trade-expression rules
sizing rules
kill criteria
reward function components
```

Loop:

```text
seed artifact
→ mutate with LLM/code generator
→ run evaluator
→ score out-of-sample
→ archive candidates
→ select/mutate/recombine
→ repeat
```

The evaluator is the moat.

## 8. RL role

RL is for sequential behavior after an environment exists.

Do not start with RL trading.

Start with:

```text
bandit: choose source diet
contextual bandit: choose source diet from company context
small POMDP: infer hidden state from costly observations
custom Gymnasium env: inspect data, submit bet card, receive reward
```

RL actions should first be information and decision actions, not live trading actions.

## 9. First code architecture

```text
fin_inference_gym/
  data/
    loaders/
    schemas.py
    point_in_time.py
  envs/
    toy_hidden_state_env.py
    historical_replay_env.py
    source_diet_env.py
  worldlets/
    guide_down.py
    margin_inflection.py
    refinancing_cliff.py
  valuation/
    dcf.py
    market_implied.py
  emissions/
    numeric_emissions.py
    transcript_feature_emissions.py
  text/
    transcript_parser.py
    feature_extractor.py
  agents/
    baselines.py
    heuristic_agents.py
    llm_agent.py
    bandit_agents.py
  evolver/
    mutate.py
    archive.py
    evaluate_candidate.py
  evaluation/
    rewards.py
    calibration.py
    tail_metrics.py
    backtest_safety.py
  experiments/
    run_toy_env.py
    run_historical_replay.py
    run_source_diet_tournament.py
  docs/
    DESIGN.md
```

## 10. Immediate build milestones

### Milestone 1 — toy POMDP without finance data

Build a toy environment where hidden state is one of four company conditions. Observations are noisy. Agent chooses which sensor to inspect and then submits a state forecast.

Success: understand hidden state, partial observation, information cost, reward.

### Milestone 2 — simple DCF engine

Build deterministic and Monte Carlo DCF functions.

Success: compute valuation distributions and market-implied assumptions.

### Milestone 3 — one-company historical replay

Replay one company across historical quarters.

Success: strict as-of-date discipline.

### Milestone 4 — transcript feature extraction

Extract 5–10 transcript features from your existing transcript database.

Success: compare transcript-feature signals against future fundamentals and returns.

### Milestone 5 — source-diet tournament

Run baseline agents with controlled source diets.

Success: identify whether text, price, options, fundamentals, or combinations add predictive value.

### Milestone 6 — AlphaEvolve mini-loop

Evolve one transcript feature formula or one source-diet rule.

Success: candidate improves out-of-sample score over baselines.

### Milestone 7 — RL information-acquisition agent

Train a small agent to choose which data source to inspect under cost before submitting a forecast.

Success: agent learns that not every source is worth inspecting in every context.

## 11. Non-negotiable engineering principles

1. Every observation must be point-in-time.
2. Every episode must have an as-of date.
3. Every future label must be separated from inputs.
4. Every source must have availability time.
5. Every evolved artifact must be evaluated out of sample.
6. Every trade card must include costs and kill criteria.
7. The system must learn to say no edge.
8. Synthetic environments are gyms, not oracles.
9. Historical replay is the anchor.
10. Live shadow evaluation is the final judge.

## 12. The first prompt to give a building AI agent

You are building the Financial Inference Gym. Do not build a trading bot, chatbot, or Wall Street workflow assistant. Build a minimal Gymnasium-compatible toy environment where:

- Hidden state is one of four company conditions: healthy, demand_weakening, margin_pressure, refinancing_stress.
- The agent can choose costly observations: fundamentals, transcript_features, price_options, macro.
- Observations are noisy emissions of hidden state.
- The agent can submit a forecast distribution over hidden states and a simple action: no_trade, long, short.
- Reward combines forecast accuracy, correct no-trade/trade decision, payoff utility, information cost, and overconfidence penalty.
- Include baseline random and heuristic agents.
- Include tests proving that observations are noisy, rewards are computed correctly, and the environment is reproducible with a random seed.

