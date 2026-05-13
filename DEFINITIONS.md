# Definitions

This file records core vocabulary for the Financial Inference Gym. Keep definitions short, operational, and tied to how the gym will work.

## Observation

An observation is information available to the agent at the time it must form a belief.

Observations are evidence, not truth.

Examples:

- Reported revenue growth
- Gross margin
- Receivables
- Transcript language
- Analyst questions
- Stock price reaction
- Options-implied move
- Macro conditions

An observation can be useful, misleading, incomplete, delayed, or contaminated by consensus.

Example:

```text
Revenue grew 18%.
```

This is an observation. It does not prove the company is healthy. It is one clue among many.

## Label

A label is the future truth or target the evaluator uses to score the agent.

The agent does not get to see the label when making its prediction. The evaluator sees it later.

Examples:

- Next-quarter revenue deceleration
- Next-quarter margin compression
- Three-month forward return
- Future drawdown
- Realized volatility
- Realized move versus options-implied move
- Guide-down event
- Hidden-state class assigned for a toy environment

Example:

```text
Revenue growth decelerated from 18% to 6% the next quarter.
```

This is a label. It is the future outcome against which the agent's earlier belief can be scored.

## Core Distinction

The agent sees observations.

The evaluator scores against labels.

```text
observation = evidence available then
label       = truth revealed later
```

If observations are treated as labels, the gym becomes fake. The goal is not to memorize visible patterns. The goal is to infer hidden reality from partial, noisy evidence.

