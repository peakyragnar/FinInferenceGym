"""
coin.py — the minimal complete instance of learning.

A box holds a coin. The coin is either:
  - "fair":   P(heads) = 0.5
  - "biased": P(heads) = 0.8

The agent never sees the coin. It sees flips.
After each flip, the agent revises its belief about which coin is in the box.

This is the atom of belief revision under evidence. Every higher layer
of the Financial Inference Gym is a variation of what happens here.
"""

import random

# The two hypotheses, each with their probability of heads.
P_HEADS = {"fair": 0.5, "biased": 0.8}


def likelihood(flip: str, coin: str) -> float:
    """How probable is this flip, if the coin really is this kind?"""
    p_heads = P_HEADS[coin]
    return p_heads if flip == "heads" else 1.0 - p_heads


def update(belief: dict, flip: str) -> dict:
    """Multiply each belief by how well it explains the flip, then renormalize."""
    unnorm = {coin: belief[coin] * likelihood(flip, coin) for coin in belief}
    total = sum(unnorm.values())
    return {coin: p / total for coin, p in unnorm.items()}


def flip_coin(coin: str, rng: random.Random) -> str:
    return "heads" if rng.random() < P_HEADS[coin] else "tails"


def run(hidden: str, n_flips: int, seed: int) -> None:
    rng = random.Random(seed)
    belief = {"fair": 0.5, "biased": 0.5}  # prior: pure ignorance, 50/50

    print(f"\nhidden coin = {hidden}   n_flips = {n_flips}   seed = {seed}")
    print(f"  start            belief(fair)=0.500  belief(biased)=0.500")

    heads = 0
    for i in range(1, n_flips + 1):
        f = flip_coin(hidden, rng)
        heads += (f == "heads")
        belief = update(belief, f)
        if i <= 10 or i % 10 == 0:
            print(
                f"  flip {i:3d} = {f:<6} "
                f"belief(fair)={belief['fair']:.3f}  "
                f"belief(biased)={belief['biased']:.3f}  "
                f"(heads so far: {heads}/{i})"
            )


if __name__ == "__main__":
    # Same seed, different hidden coins. The agent has identical priors
    # in both runs. The only thing that differs is the truth in the box.
    run(hidden="biased", n_flips=100, seed=42)
    run(hidden="fair",   n_flips=100, seed=42)
