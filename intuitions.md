# Intuitions

This document stays brief. It records the core intuitions Michael needs to internalize as the Financial Inference Gym is built layer by layer.

It is organized by intuition bucket, not as a long numbered ladder.

## 1. Hidden Company State

### a. Core Claim

A company is not the same thing as its visible data.

The real object is the hidden economic state of the company:

```text
hidden company reality
  -> emits noisy observations
  -> agent forms a belief
  -> market expresses its own belief through price/options
  -> evaluator scores whether the agent's belief was better
```

Financial data is not truth. It is evidence.

### b. Noisy Emissions

Examples of noisy emissions:

- Reported revenue growth
- Margins
- Receivables
- Inventory
- Management tone
- Analyst questions
- Stock price reaction
- Options-implied move
- News sentiment

The agent's first job is not to summarize these emissions. The agent's job is to infer the hidden state that generated them.

### c. Why This Matters

Markets usually do not misprice obvious information for long.

The opportunity is more likely to come from ambiguous or contradictory evidence:

```text
reported numbers look fine
but receivables are rising
and Q&A pressure is increasing
and management language is evasive
and options imply a small move
```

A shallow system says:

```text
good quarter
```

A better inference system might say:

```text
demand is weakening underneath the reported numbers
```

That is the primitive the gym must train.

### d. Core Loop

The project is built around this loop:

```text
hidden state
  -> noisy emissions
  -> belief update
  -> market-belief comparison
  -> scored forecast / bet card
```

The evaluator should not ask whether an agent sounded intelligent.

It should ask:

- Did the agent infer the hidden state?
- Was the agent calibrated?
- Did the agent separate signal from noise?
- Did the agent identify a gap between its belief and market-implied belief?
- Was that gap tradable after costs, timing, uncertainty, and risk?

Money comes later. First, the system must learn to form better beliefs.
