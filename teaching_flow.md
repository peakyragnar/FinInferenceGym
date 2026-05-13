Yes. I see the dilemma exactly.

You are trying to build something genuinely new, but the primitives are not yet fully internalized:

* AlphaEvolve intuition: how to search over artifacts under an evaluator.
* RL intuition: how an agent learns behavior from state/action/reward loops.
* Finance-gym intuition: how hidden economic states emit observations and how agents infer mispriced future-world distributions.
* Engineering intuition: how to build this without creating an overcomplicated fake market.

The wrong move is to pause everything and “go learn RL” in the abstract.

The other wrong move is to ask an AI coding agent to build the full finance gym immediately.

The correct move is:

Build the project as a curriculum. Each toy system teaches one primitive, and each toy system becomes a component of the real system.

I created a canonical v0.1 design document you can feed to a building AI agent here: Financial Inference Gym — Canonical Design Document v0.1￼.

The core decision

Do not build the full project yet.

Build the teaching sequence that leads into the project.

The canonical sequence should be:

1. AlphaEvolve intuition
   → evolve small code artifacts under hard evaluators.
2. Bandit intuition
   → learn source selection without full RL complexity.
3. POMDP intuition
   → infer hidden state from noisy observations.
4. Gymnasium environment intuition
   → implement reset(), step(), observation, action, reward.
5. Finance toy worldlet
   → hidden company state emits fundamentals, transcript features, price/options features.
6. Historical replay
   → replace synthetic emissions with real historical company episodes.
7. AlphaEvolve inside the finance gym
   → evolve source diets, transcript features, valuation rules, and bet templates.
8. RL inside the finance gym
   → agent learns what to inspect, when to stop, when to trade, when to say no edge.

That is the path.

Why this resolves the dilemma

You do not need to master RL before building.

You need to understand RL through the exact shape of your problem.

RL is not one monolithic thing. The OpenAI Spinning Up material frames RL around states, actions, trajectories, policies, rewards, and value functions; that is the vocabulary you need, not a PhD-level tour of every RL algorithm.  ￼

Your first RL intuition should not be PPO, SAC, Dreamer, MuZero, or giant self-play systems.

Your first RL intuition should be:

The agent is allowed to buy information before making a decision. Some information helps. Some is noise. Some is expensive. The agent must learn what to inspect and when to stop.

That maps directly to your finance problem.

The most important reframing

You are not building:

AI reads all data → AI generates alpha

You are building:

hidden state exists
→ observations are partial/noisy/biased
→ market has a belief expressed in price/options
→ agent forms a different belief
→ agent decides whether the belief gap is monetizable
→ evaluator scores calibration, payoff, and reasoning path

That is a partially observable inference game.

The gym is not the market. The gym is the training ground for the inference problem.

What to learn first: not “RL,” but four RL-shaped problems

1. Multi-armed bandit

This is the smallest intuition.

The agent chooses one of several actions and gets a reward.

Finance translation:

Actions:
  read fundamentals
  read transcript
  read options surface
  read macro
  read news
  say no edge
Reward:
  how much the chosen source improved forecast accuracy minus cost

This teaches:

exploration vs exploitation
reward
information value
source selection

No complex environment. No long horizon. No neural network needed.

2. Contextual bandit

Now the agent gets context before choosing.

Finance translation:

Context:
  company sector
  recent return
  earnings proximity
  valuation
  options implied move
  transcript feature summary
Action:
  choose source diet
Reward:
  forecast improvement / payoff / calibration

This teaches:

source diets conditional on context

Example insight the agent might learn:

For enterprise software before earnings, transcript Q&A features matter.
For liquidity shocks, price/options matter.
For refinancing risk, balance sheet + credit spreads matter.

This is already close to your source-diet thesis.

3. Toy POMDP

Now there is a hidden state.

Finance translation:

Hidden company state:
  healthy
  demand_weakening
  margin_pressure
  refinancing_stress
Observations:
  fundamentals are noisy
  transcripts are noisy
  price/options are noisy
  macro is noisy
Agent:
  chooses what to inspect
  forms belief
  submits forecast / bet card

This teaches the real core:

belief under uncertainty
partial observability
costly information
confidence calibration

4. Custom Gymnasium environment

Now you put the toy POMDP into a standard environment interface.

Gymnasium is the maintained standard API for RL environments; its Env class is built around reset() and step() and can represent partially or fully observed single-agent environments.  ￼

Your first environment should be tiny:

obs, info = env.reset()
for step in range(max_steps):
    action = agent.act(obs)
    obs, reward, terminated, truncated, info = env.step(action)

The finance version:

reset:
  choose company episode
  choose hidden state
  emit initial observation
step:
  agent chooses inspect_source or submit_bet_card
  environment emits new observation or final reward

That is the first real gym.

Where AlphaEvolve fits in your learning sequence

You are currently learning AlphaEvolve. Keep doing that. It is the right first primitive because it trains the most important instinct:

You only get discovery if the evaluator is real.

DeepMind describes AlphaEvolve as combining Gemini models with automated evaluators and an evolutionary framework that verifies, runs, scores, and improves candidate programs.  ￼ Google Cloud’s description is even more directly useful for your build: AlphaEvolve-style use requires a problem specification, evaluator logic, and a seed program; then models mutate candidates and the evolutionary loop selects better ones.  ￼

For your finance gym, AlphaEvolve should first evolve tiny artifacts.

Do not start with:

evolve a trading strategy

Start with:

evolve a transcript feature formula
evolve a source-diet rule
evolve a DCF assumption rule
evolve a guide-down-risk score
evolve a market-implied inversion formula

Example first AlphaEvolve exercise:

Given toy hidden company states and noisy observations,
evolve a scoring function that predicts hidden state better than baseline.

Then:

Given historical transcript features,
evolve a formula that predicts next-quarter revenue deceleration.

Then:

Given price/options/fundamentals/transcript features,
evolve a source-diet policy that improves forecast calibration.

This lets AlphaEvolve become part of the project without prematurely trying to discover real alpha.

The canonical build ladder

Here is the build path I would follow.

Milestone 0 — canonical document

Done.

Use this as the root design brief: Financial Inference Gym — Canonical Design Document v0.1￼.

Do not feed the whole project to an AI coding agent at once. Feed it one milestone at a time.

Milestone 1 — toy hidden-state gym

Build a tiny environment.

Hidden state:

healthy
demand_weakening
margin_pressure
refinancing_stress

Available observations:

fundamentals
transcript_features
price_options
macro

Actions:

inspect_fundamentals
inspect_transcript_features
inspect_price_options
inspect_macro
submit_no_trade
submit_long
submit_short

Reward:

+ correct hidden-state forecast
+ correct trade/no-trade decision
+ payoff utility
- information cost
- overconfidence

This teaches the shape of the real system.

Milestone 2 — bandit source selection

Before full RL, build a source selector.

Question:

Given context, which source is worth inspecting?

This is directly relevant to your thesis that not all information is useful and some information contaminates judgment.

Milestone 3 — deterministic DCF engine

Build boring DCF functions:

forecast cash flows
discount them
compute equity value
invert market price into implied assumptions

No AI. No RL. No AlphaEvolve.

This gives you the finance physics.

Milestone 4 — Monte Carlo DCF distribution

Upgrade DCF from one answer to distributions:

P5
P25
P50
P75
P95
left-tail probability
right-tail probability

This teaches the “future possible worlds” intuition.

Milestone 5 — transcript feature extraction

Use your real transcript database.

Extract 5–10 primitive features:

demand softness
sales-cycle elongation
pricing power
management confidence
management evasiveness
analyst pressure
inventory pressure
guidance specificity
margin pressure

Do not worry yet about perfect NLP. Start crude and measurable.

Milestone 6 — historical replay, one company

Pick one company.

At each historical earnings call date:

agent sees only data available as of that date
agent forecasts future fundamentals and return distribution
environment advances
evaluator scores

This teaches point-in-time discipline.

Milestone 7 — historical replay, 100 companies

Now scale.

Run baseline agents:

random
price-only
fundamentals-only
transcripts-only
price + options
fundamentals + transcripts
full context

This is where you begin testing source diets.

Milestone 8 — AlphaEvolve over toy artifacts

Use AlphaEvolve-style search to evolve:

guide-down-risk formula
transcript-feature weighting
source-diet rule
valuation-sensitivity rule

The goal is not real alpha yet.

The goal is to learn whether the evolver can improve artifacts under a hard evaluator.

Milestone 9 — RL information-acquisition agent

Now RL enters.

The RL agent chooses:

inspect transcript?
inspect options?
inspect macro?
inspect peer transcript?
stop and submit?
say no edge?

This is the first finance-native RL problem.

Use simple algorithms before deep RL. CleanRL is a good learning library because it provides single-file implementations of RL algorithms, which makes it easier to inspect what is actually happening instead of treating the algorithm as a black box.  ￼ Stable-Baselines3 is useful later when you want reliable PyTorch implementations of standard algorithms rather than maximum educational transparency.  ￼

What the first AI-coding prompt should be

Do not ask:

Build the full financial inference gym.

Ask:

Build a minimal Gymnasium-compatible toy environment called HiddenCompanyStateEnv.
Hidden states:
  healthy
  demand_weakening
  margin_pressure
  refinancing_stress
Actions:
  inspect_fundamentals
  inspect_transcript_features
  inspect_price_options
  inspect_macro
  submit_no_trade
  submit_long
  submit_short
Each inspect action costs reward and returns a noisy observation correlated with hidden state.
Submission actions terminate the episode.
Reward should combine:
  correct hidden-state inference
  correct trade/no-trade decision
  payoff utility
  information cost
  overconfidence penalty
Include:
  random baseline agent
  simple heuristic agent
  unit tests
  reproducible seeding
  small experiment script

That is the first build.

If that works, you have the skeleton of the real thing.

The right learning rhythm

Your learning rhythm should be:

learn concept
build toy
run experiment
inspect failure
write evaluator
only then scale

For example:

Concept:
  partial observability
Toy:
  hidden company state with noisy observations
Experiment:
  compare random agent vs heuristic agent
Failure:
  transcript feature too informative / too useless
Evaluator:
  calibration + cost + overconfidence
Scale:
  add real transcript features

This is how you build intuition.

What not to do

Do not start with multi-agent RL.

Do not start with options microstructure.

Do not start with synthetic generated transcripts.

Do not start with full S&P 1500.

Do not start with live trading.

Do not start with a giant memory agent.

Do not start with “AI reads everything.”

Do not start with a transformer world model.

Every one of those is a complexity trap.

The deeper principle

You are trying to build two things at once:

1. A system.
2. Your own operating intuition for the system.

So the project must be designed pedagogically.

The build path should teach you:

AlphaEvolve teaches:
  evaluator-driven discovery
Bandits teach:
  source selection and information value
POMDPs teach:
  hidden-state inference
Gymnasium teaches:
  environment/action/reward structure
DCF engine teaches:
  finance physics
Historical replay teaches:
  point-in-time evaluation
Transcript features teach:
  noisy textual emissions
RL teaches:
  sequential information acquisition and decision policy

That is the correct order.

My recommendation

Continue learning AlphaEvolve, but narrow the exercise.

Your next AlphaEvolve practice should not be abstract coding puzzles anymore. It should be a toy finance artifact.

Example:

Evolve a hidden-state scoring function in the toy company environment.

Then learn RL through the same toy environment.

That gives you convergence:

AlphaEvolve improves artifacts.
RL improves behavior.
The finance gym supplies the environment.
The evaluator decides what survives.

That is the architecture.

The dilemma is real, but it has a clean answer:

Do not learn first and build later. Build the curriculum-version of the project, and let that teach you the primitives.