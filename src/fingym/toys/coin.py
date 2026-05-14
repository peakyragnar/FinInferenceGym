"""coin.py — the minimal complete instance of learning.

A box holds a coin. The coin is either:
  - "fair":   P(heads) = 0.5
  - "biased": P(heads) = 0.8

The agent never sees the coin. It sees flips.
After each flip, the agent revises its belief about which coin is in the box.

This is the atom of belief revision under evidence. Every higher layer of
the gym is a variation of what happens here. See intuitions.md #1 ("Belief
Revision Under Evidence") and #3 ("The Hidden State Is the Real Object").

The state alphabet (Coin) and emission alphabet (Flip) are encoded as
Literal types so mypy enforces the closed hypothesis space at the type
level. The math itself respects Cromwell's rule — no probability is sent
to exactly 0 or 1 by an update — as long as priors start strictly inside
(0, 1).

Run: `uv run python -m fingym.toys.coin`
"""

import random
from typing import Literal

type Coin = Literal["fair", "biased"]
type Flip = Literal["heads", "tails"]
type Belief = dict[Coin, float]

# Likelihood model: P(heads | coin).
P_HEADS: dict[Coin, float] = {"fair": 0.5, "biased": 0.8}


def likelihood(flip: Flip, coin: Coin) -> float:
    """P(flip | coin) — how probable this flip is, given this coin kind."""
    p_heads = P_HEADS[coin]
    return p_heads if flip == "heads" else 1.0 - p_heads


def update(belief: Belief, flip: Flip) -> Belief:
    """One Bayesian update: posterior = prior * likelihood / normalize."""
    unnorm: Belief = {coin: belief[coin] * likelihood(flip, coin) for coin in belief}
    total = sum(unnorm.values())
    return {coin: p / total for coin, p in unnorm.items()}


def flip_coin(coin: Coin, rng: random.Random) -> Flip:
    """Emit one flip from the given coin."""
    return "heads" if rng.random() < P_HEADS[coin] else "tails"


def run(hidden: Coin, n_flips: int, seed: int) -> None:
    """Run a single inference episode and print belief evolution."""
    rng = random.Random(seed)
    belief: Belief = {"fair": 0.5, "biased": 0.5}

    print(f"\nhidden coin = {hidden}   n_flips = {n_flips}   seed = {seed}")
    print("  start            belief(fair)=0.500  belief(biased)=0.500")

    heads = 0
    for i in range(1, n_flips + 1):
        f = flip_coin(hidden, rng)
        heads += f == "heads"
        belief = update(belief, f)
        if i <= 10 or i % 10 == 0:
            print(
                f"  flip {i:3d} = {f:<6} "
                f"belief(fair)={belief['fair']:.3f}  "
                f"belief(biased)={belief['biased']:.3f}  "
                f"(heads so far: {heads}/{i})"
            )


if __name__ == "__main__":
    # Same seed, different hidden coins. The agent's prior is identical
    # in both runs. The only thing that differs is the truth in the box.
    run(hidden="biased", n_flips=100, seed=42)
    run(hidden="fair", n_flips=100, seed=42)
