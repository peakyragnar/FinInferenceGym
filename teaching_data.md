Download episode data first, not “all data.”

The unit of the gym should be:

company × event_date/as_of_date → observations available then → future outcome

Not:

giant lake of prices + transcripts + macro + options

The first objective is to create replayable company-quarter episodes where an agent can inspect partial observations and be scored against future fundamentals and future returns.

My direct answer

Start with this order:

1. Security master / ticker-CIK map / transcript-company map
2. Daily equity prices + corporate actions
3. Your transcript metadata + transcript text
4. SEC or vendor fundamentals
5. FRED/ALFRED macro vintages
6. Derived transcript features
7. Options-derived event features
8. News only later, as a narrative/attention sensor

Do not start with full options tick data, news, social data, intraday equity quotes, or all FRED series. Those are complexity traps.

And on Prime Intellect / Tinker:

Do not incorporate either into v0. Build the local gym first.
Later, Prime Intellect is more aligned with RL environment training, while Tinker is more aligned with LLM fine-tuning / post-training once you have rollouts or supervised examples.

Keep your architecture compatible with them, but do not make either one a dependency yet.

⸻

1. The first dataset: company_quarter_episode_v0

This is what you should build first.

Each row is one company at one historical moment, usually an earnings-call date or filing date.

episode_id
company_id
ticker
cik
sector
fiscal_year
fiscal_quarter
event_type
event_date
as_of_date

The as_of_date is crucial. It means:

“The agent is standing here in time. What is it allowed to know?”

Then attach observations:

price_features_as_of_date
fundamental_features_as_of_date
macro_features_as_of_date
transcript_text_available_as_of_date
transcript_features_as_of_date
option_features_as_of_date

And attach labels:

future_return_1m
future_return_3m
future_return_6m
future_return_12m
future_revenue_growth_next_q
future_margin_change_next_q
future_earnings_surprise_if_available
future_drawdown_3m
future_realized_volatility
future_realized_move_vs_implied_move

That is the gym’s first real object.

Everything else is downstream.

⸻

2. Download package zero: security master

Before prices, fundamentals, or transcripts, you need identity resolution.

Create this:

company_id
ticker
ticker_start_date
ticker_end_date
cik
company_name
exchange
sector
industry
sic
country
is_active
is_delisted
transcript_company_name
transcript_db_identifier

Why first?

Because every dataset will disagree about company identity.

A company may have:

ticker changes
mergers
spin-offs
old CIKs
renamed entities
dual share classes
delistings
transcript naming mismatches

If you do not solve this first, every later result becomes polluted.

For v0, do not try to solve all 1,700 companies. Pick 100–300 companies from your transcript database where the ticker mapping is clean.

⸻

3. Download package one: daily equity prices

Start with daily bars, not trades and quotes.

From Massive, download daily stock aggregate bars for your initial universe:

date
ticker
open
high
low
close
volume
vwap if available
transactions if available

Massive’s stock flat files include historical trades, quotes, and aggregate market data, and the docs specifically describe flat files as useful for backtesting, research, and large-scale historical analysis. The same docs warn that stock flat files are unadjusted and that prices/volumes are not adjusted for splits, dividends, or other corporate actions, so you need corporate-action handling or adjusted REST results for return calculations. Massive also notes that timestamps are Unix UTC timestamps and must be converted carefully to Eastern Time for market-session alignment.  ￼

For the first gym, you need these derived labels:

return_1d
return_5d
return_21d
return_63d
return_126d
return_252d
max_drawdown_63d
max_drawdown_126d
realized_vol_21d
realized_vol_63d
gap_after_event
post_earnings_drift

Also download:

splits
dividends
ticker changes if available
delisting information if available

Do not build a gym on unadjusted prices unless you are explicitly modeling corporate actions. A split or large dividend can look like a catastrophic return if mishandled.

First equity download target:

Universe:
  100–300 companies from your transcript DB
Period:
  last 10 years, matching your transcript history
Granularity:
  daily adjusted OHLCV or daily unadjusted + corporate actions
Do not download first:
  full trade ticks
  full quote ticks
  full intraday history

⸻

4. Download package two: transcript metadata and raw transcripts

Your transcript database is central. It should not just be text blobs.

First normalize the metadata:

transcript_id
company_id
ticker
fiscal_year
fiscal_quarter
call_date
available_at
source
event_type
full_text

Then split it:

transcript_turns
  transcript_id
  turn_id
  speaker_name
  speaker_role
  section              -- prepared remarks / Q&A
  text

Then chunk it:

transcript_chunks
  chunk_id
  transcript_id
  section
  speaker_role
  text
  token_count

Do not extract fancy features yet. First make sure you can answer:

For ticker XYZ on date 2021-08-05, which transcripts were available?
What were the prior 4 calls?
What was the Q&A text?
Who was speaking?
What quarter did the transcript correspond to?

Your first replay episodes should be anchored around transcript dates:

episode date = earnings call date or next trading day
agent observation = transcript + price + fundamentals + macro as of that date
future outcome = next 1m/3m/6m returns + next-quarter fundamentals

This is where the gym becomes real.

⸻

5. Download package three: fundamentals

You need fundamentals because the hidden state is economic, not just textual.

Minimum fields:

revenue
gross_profit
operating_income
EBIT
EBITDA if available
net_income
EPS
cash_from_operations
capex
free_cash_flow
cash
debt
net_debt
shares_outstanding
working_capital
accounts_receivable
inventory
deferred_revenue
gross_margin
operating_margin
FCF_margin
net_debt_to_EBITDA

If Massive’s pricing tier does not give you fundamentals, use SEC EDGAR APIs first. The SEC says data.sec.gov hosts RESTful JSON APIs for company submissions and extracted XBRL data, and that the APIs include submissions history and XBRL data from financial statements such as 10-Ks and 10-Qs. The SEC also says these APIs do not require authentication or API keys.  ￼

For the gym, store fundamentals with filing availability:

period_end_date
filing_date
accepted_at
available_at
fiscal_year
fiscal_quarter
statement_type
metric
value
source

Why this matters:

Quarter ended:       2021-06-30
Earnings call:       2021-08-03
10-Q filed:          2021-08-06
Simulator date:      2021-08-04

On 2021-08-04, the agent may have the earnings release and transcript, but not necessarily the filed 10-Q. That distinction matters if you later want true point-in-time replay.

For v0, you can start rough:

Use quarterly fundamentals aligned to earnings date.
Mark the point-in-time limitation.
Fix it later with SEC accepted_at timestamps.

But do not forget this issue.

⸻

6. Download package four: FRED/ALFRED macro

Do not download all of FRED.

FRED has an enormous universe, but your first gym needs maybe 20–40 series. FRED’s API has a real-time/vintage concept: the docs say the real-time period marks when information was known, defaults to today, and ALFRED users can retrieve information known as of a past period by setting realtime_start and realtime_end.  ￼ The FRED series/vintagedates endpoint returns dates when a series was revised or newly released.  ￼

For a finance gym, use macro as a regime sensor, not as a prediction oracle.

Start with these categories:

Rates:
  Fed funds
  2-year Treasury
  10-year Treasury
  term spread
  SOFR or short-rate proxy
Inflation:
  CPI
  core CPI
  PCE
  PPI
Labor:
  unemployment rate
  nonfarm payrolls
  initial claims
Growth:
  real GDP
  industrial production
  retail sales
  housing starts
  durable goods
Credit / risk:
  investment-grade credit spread
  high-yield spread
  Baa / Aaa spreads
  VIX if using FRED VIX series
Liquidity / financial conditions:
  Fed balance sheet
  financial conditions index if available
Commodities / FX:
  WTI oil
  dollar index proxy

For v0, store:

series_id
observation_date
value
realtime_start
realtime_end
vintage_date
release_date if available

The first macro feature table should be small:

macro_features_as_of_date
  as_of_date
  fed_funds
  ten_year_yield
  two_year_yield
  term_spread
  unemployment
  cpi_yoy
  ppi_yoy
  industrial_production_yoy
  retail_sales_yoy
  housing_starts_yoy
  high_yield_spread
  oil_price

Do not allow revised macro values to leak into historical replay.

⸻

7. Download package five: transcript features

Only after transcript metadata is clean should you extract features.

Start with 8–10 features, not 100.

demand_softness_score
sales_cycle_elongation_score
pricing_power_score
margin_pressure_score
inventory_pressure_score
management_confidence_score
management_evasiveness_score
analyst_pressure_score
guidance_specificity_score
backlog_uncertainty_score

Then compute deltas:

feature_delta_vs_prior_q
feature_delta_vs_prior_4q
feature_zscore_vs_company_history
feature_zscore_vs_sector_history

This is where the first AlphaEvolve-style search can operate.

Example candidate artifact:

guide_down_risk =
    0.35 * sales_cycle_elongation_delta
  + 0.25 * analyst_pressure_delta
  + 0.20 * management_evasiveness
  - 0.10 * guidance_specificity
  + 0.10 * margin_pressure_delta

Evaluator:

Does this predict:
  next-quarter revenue deceleration?
  margin compression?
  guidance cut?
  negative 3-month return?
  realized move exceeding options-implied move?

This is the first place where “new idea generation” becomes concrete.

⸻

8. Download package six: options features, not raw options data

Options matter because they reveal the market-implied distribution.

But do not ingest every option trade/quote first.

Massive’s options flat files cover trades, quotes, and aggregate market data sourced from OPRA across U.S. options exchanges, and the docs say the flat files contain transaction-level trades, comprehensive bid/ask quotes, and minute/daily aggregates. That is powerful, but it is also a lot of data.  ￼

For the first gym, you only need event-level options features around earnings/transcript dates:

as_of_date
ticker
underlying_price
nearest_expiry
days_to_expiry
atm_call_mid
atm_put_mid
atm_straddle_mid
implied_move_pct
atm_iv
put_skew_25_delta
call_skew_25_delta
term_structure_front_to_next
open_interest_total
volume_total
option_liquidity_score
bid_ask_width_score

Massive’s option-chain snapshot endpoint is directly relevant because it consolidates contract-level pricing details, Greeks, implied volatility, quotes, trades, open interest, and underlying price for all options contracts associated with an underlying ticker.  ￼

For v0, pull snapshots only for:

T-5 trading days before earnings call
T-1 trading day before earnings call
T+1 trading day after earnings call

Then compute:

implied_move_pre_event
realized_move_post_event
realized_minus_implied
skew_pre_event
iv_change_post_event
liquidity_score

The first options label you want:

Did realized move exceed implied move?

That lets the gym test:

Did transcripts/fundamentals reveal a tail risk that options underpriced?

That is much more important than building an options backtester on day one.

⸻

9. News should come later

Do not download news first.

News is useful, but not as truth. It should be a narrative/attention sensor.

Massive has stock-news endpoints that return ticker-related news/article data, but for your gym news should be used to measure public attention, sentiment velocity, narrative consensus, and possible hive-mind contamination, not as a primary truth source. Massive’s stock news docs describe ticker-related articles with fields like article content/metadata and related tickers.  ￼

Add news after:

prices
transcripts
fundamentals
macro
options event features

News features should look like:

news_volume_delta
headline_sentiment_delta
narrative_velocity
topic_cluster
source_count
post_event_explanation_score
consensus_contamination_score

The gym question is not:

What does the news say?

It is:

Has the public narrative already incorporated the hidden-state signal?

Example:

Transcript features deteriorate.
Options imply a small move.
News remains bullish.
Market price is strong.

That is a possible anti-consensus short setup.

⸻

10. The first actual data build

Do this first:

Universe:
  100 companies from your transcript DB
Period:
  10 years
Episode anchor:
  earnings call date / transcript available date
Observation date:
  next trading day after earnings call
Data:
  daily stock prices
  corporate actions
  quarterly fundamentals
  raw transcript text
  basic transcript metadata
  20–40 macro series, ideally vintage-aware
  options event features if available
Labels:
  1m return
  3m return
  6m return
  next-quarter revenue growth
  next-quarter margin change
  realized move vs implied move
  max drawdown over 3m

This gives you perhaps:

100 companies × 10 years × 4 quarters = ~4,000 episodes

That is enough to learn the intuitions.

Do not start with 1,700 companies. That sounds productive, but it will bury you in data-cleaning problems before the gym exists.

⸻

11. What should the first gym ask?

The first gym should not ask:

Can the agent generate alpha?

Too vague.

It should ask four smaller questions.

Question 1: hidden state inference

Given available observations, can the agent infer:
  demand weakening
  margin pressure
  refinancing stress
  upside inflection
  no edge

Question 2: future fundamental distribution

Can the agent forecast:
  next-quarter revenue growth
  next-quarter margin change
  probability of guide-down

Question 3: future return distribution

Can the agent forecast:
  1m/3m/6m return distribution
  left-tail risk
  right-tail potential

Question 4: market-implied mismatch

Did options or price underprice the likely move?

That is enough for v0.

⸻

12. The minimum schema

You want these tables first:

companies
securities
ticker_history
corporate_actions
prices_daily
returns_daily
events_earnings
transcripts_raw
transcript_turns
transcript_chunks
transcript_features
fundamentals_quarterly
fundamentals_annual
macro_observations
macro_features_as_of
options_event_features
episodes
episode_observations
episode_labels
episode_predictions
episode_scores

The key table is episodes.

Example:

episodes
  episode_id
  company_id
  ticker
  fiscal_year
  fiscal_quarter
  event_date
  as_of_date
  sector
  has_transcript
  has_fundamentals
  has_options
  has_macro

Then labels:

episode_labels
  episode_id
  return_1m
  return_3m
  return_6m
  realized_vol_1m
  max_drawdown_3m
  next_q_revenue_growth
  next_q_operating_margin_change
  realized_move_vs_implied

That is the gym dataset.

⸻

13. Should you incorporate Prime Intellect?

Not in v0. Maybe in v2.

Prime Intellect is interesting because it is explicitly building around self-improving agents, RL post-training, environments, evals, and inference. Their site says their stack supports training, deployment, continuous improvement, compute, RL post-training, environments, evals, and inference. It also describes an Environment Hub with 2,500+ open-source RL environments and hosted training for large-scale models optimized for agentic workflows.  ￼

That is directionally aligned with what you want.

But you do not yet have the thing Prime would train on.

You first need:

local gym
episodes
reward function
baseline agents
source-diet experiments
rollouts
evals

Only then does Prime become useful.

Use Prime Intellect when you can say:

Here is my environment.
Here are my observations.
Here are my actions.
Here is my reward.
Here are my baselines.
Now I want hosted RL training / scalable rollout generation / model post-training.

Until then, it is infrastructure ahead of science.

My recommendation:

v0:
  no Prime dependency
v1:
  package your local environment in a clean Gymnasium-like interface
v2:
  test whether Prime can host your custom environment and train an information-acquisition policy
v3:
  use Prime for larger-scale RL only if local experiments show signal

Prime is more relevant than Tinker for the RL gym side.

⸻

14. Should you incorporate Tinker?

Also not in v0. Later, yes, but for a different role.

Tinker is a cloud training API. Thinking Machines’ docs say it lets you write training loops locally while Tinker handles the GPUs, and that it supports LoRA fine-tuning for open-weight models from 1B to 1T+ parameters.  ￼ Their quickstart explicitly walks through both supervised fine-tuning and reinforcement-learning workflows: SFT imitates examples, while RL samples rollouts, computes rewards/logprobs, performs forward/backward passes with importance sampling, and updates weights.  ￼

That is useful after you have training data.

Tinker is not the gym. Tinker is not the evaluator. Tinker is not the finance engine.

Tinker is useful when you have:

SFT examples:
  transcript → hidden-state forecast
  company episode → bet card
  observations → calibrated distribution
RL rollouts:
  agent chooses source inspections
  agent submits forecast/action
  reward computed by your environment

Then you can use Tinker to fine-tune:

transcript-reading model
episode-reasoning model
bet-card generator
information-acquisition agent

My recommendation:

v0:
  no Tinker dependency
v1:
  generate supervised examples from historical replay
v2:
  use Tinker for small LoRA experiments on transcript-reading / bet-card generation
v3:
  use Tinker RL only after reward functions are stable

Tinker is more relevant for model post-training than for the first environment build.

⸻

15. Prime Intellect vs Tinker for this project

Need	Use now?	Better fit
Download finance data	No	neither
Build local simulator	No	neither
Define environment/reward	No	local Python
Run source-diet tournaments	No	local first
Train RL agent on custom env	Later	Prime Intellect likely more natural
Fine-tune LLM on transcript/bet-card examples	Later	Tinker likely more natural
Scale rollouts/evals	Later	Prime Intellect
LoRA train open model	Later	Tinker
Deploy custom model	Later	either, depending stack

So the decision is:

Do not incorporate either yet.
Design clean adapters so you can incorporate them later.

Adapter interfaces:

class FinanceGymEnv:
    def reset(self, seed=None):
        ...
    def step(self, action):
        ...
    def render_observation(self, source_diet):
        ...
    def score_prediction(self, prediction):
        ...
class TrainingBackend:
    def run_sft(self, dataset, model, config):
        ...
    def run_rl(self, env, model, reward_fn, config):
        ...

Then later:

LocalTrainingBackend
PrimeIntellectBackend
TinkerBackend

No lock-in. No premature dependency.

⸻

16. What I would download this week

Concrete sequence:

Day 1–2: company identity + episodes

Pick 100 companies from transcript DB.
Map ticker → CIK → company_id.
Create earnings/transcript event table.
Create episode table.

Day 3–4: stock daily bars

Download 10 years daily OHLCV for those 100 companies.
Download splits/dividends/corporate actions.
Compute adjusted returns and future labels.

Day 5–6: transcripts

Normalize raw transcripts.
Split into prepared remarks / Q&A.
Split into speaker turns.
Attach transcript_available_date.
Attach each transcript to an episode.

Day 7–9: fundamentals

Pull quarterly revenue, margins, FCF, debt, cash, shares.
Use SEC companyfacts/submissions if Massive financials are not available.
Align by filing/availability date as best as possible.

Day 10: macro

Pull 20–40 FRED/ALFRED macro series.
Create macro_features_as_of_date.
Start with vintage-aware where practical.

Day 11–14: first gym baseline

Create observations.
Create labels.
Run baseline agents:
  random
  price-only
  fundamentals-only
  transcript-only
  price+fundamentals
  price+fundamentals+transcript

Do options after this unless the options pipeline is trivial.

⸻

17. What I would not download yet

Do not download first:

full options quote history
full options trade history
minute-level equity quotes
all Massive flat files
all FRED series
all news
social media
sell-side reports
alternative data
full 1,700-company universe

Those are not wrong eventually. They are wrong first.

The first goal is not data coverage.

The first goal is:

Can the environment produce replayable episodes where different source diets can be scored?

⸻

18. The exact first experiment

Once the first 100-company dataset exists, run this:

For every earnings-call episode:
Agent A sees:
  price only
Agent B sees:
  fundamentals only
Agent C sees:
  transcript only
Agent D sees:
  fundamentals + transcript
Agent E sees:
  price + fundamentals + transcript + macro
Each agent predicts:
  next-quarter revenue deceleration probability
  next-quarter margin-compression probability
  3-month return distribution
  left-tail probability
  no-edge/trade flag
Evaluator scores:
  calibration
  Brier/log score
  realized 3-month return
  tail-event detection
  false positives

This is the first real test of your thesis.

Not alpha yet.

But it answers:

Does transcript-derived information add predictive signal?
Does price contaminate or improve judgment?
Does full context outperform restricted source diets?
Can the system identify no-edge cases?

That is the foundation.

⸻

Bottom line

Download first:

security master
daily stock prices
corporate actions
transcripts
quarterly fundamentals
macro vintages

Then derive:

episodes
labels
transcript features
source-diet observations

Add options next, but only as event-level implied-distribution features, not raw OPRA firehose.

Add news later as a narrative/attention/contamination layer, not as truth.

Do not incorporate Prime Intellect or Tinker yet. Build the local gym and first source-diet tournament. Once you have episodes, rewards, baselines, and rollouts, use Prime Intellect for scalable RL/environment training and Tinker for model fine-tuning/post-training.