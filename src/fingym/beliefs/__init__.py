"""Belief recovery and edge calculation.

Recovers the market's implied belief about hidden state from observable
emissions (price, options chain, implied volatility), then computes the
edge between the agent's belief and the market's.

Three canonical inversions (DESIGN.md "The Six Layers" + Intuition 11):
  - implied_dcf: revenue growth, margins, discount rate that justify
    the current stock price
  - options_implied: probability distribution over future price moves
    extracted from option prices
  - edge: agent_belief − market_implied_belief, net of costs

Per Intuition 11: edge is calibrated disagreement that clears costs.
Three conditions must all hold for a real trade: disagreement with the
market, calibration of the agent's stated confidence, gap large enough
to survive costs and time.

Architectural import boundary:
  - This package is read by agents/, cli/.
  - This package MUST NOT import from agents/, evaluator/, llm/, memory/.
"""
