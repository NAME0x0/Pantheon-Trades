"""Direction-aware helpers shared across services.

Boule decides direction from oracle vs market probability. Areopagus and
Strategos then need to translate that direction back into a magnitude-aware
edge for Kelly sizing, slippage estimation, and order placement.
"""

from __future__ import annotations

from typing import Literal

Direction = Literal["YES", "NO"]


def infer_direction(market_probability: float, oracle_probability: float) -> Direction:
    """Pick the side our oracle estimate disagrees with the market on."""
    return "YES" if oracle_probability >= market_probability else "NO"


def directional_edge(market_probability: float, oracle_probability: float, direction: Direction) -> float:
    """Signed edge that always reads as positive when the trade has alpha.

    For YES: oracle - market (positive when we expect YES to resolve higher).
    For NO:  market - oracle (positive when we expect NO to win).
    """
    if direction == "YES":
        return oracle_probability - market_probability
    return market_probability - oracle_probability


def entry_price(market_probability: float, direction: Direction) -> float:
    """Effective entry price for the contract we are buying."""
    return market_probability if direction == "YES" else 1.0 - market_probability
