"""Arbitrage detector — flag YES + NO prices that don't sum to ~1."""

from __future__ import annotations


ARB_TOLERANCE = 0.02


def detect_arbitrage(yes_price: float, no_price: float) -> str | None:
    total = yes_price + no_price
    if total <= 0 or total > 2:
        return f"degenerate prices yes={yes_price:.3f} no={no_price:.3f}"
    gap = abs(total - 1.0)
    if gap >= ARB_TOLERANCE:
        return f"arb candidate: yes+no={total:.3f} (gap {gap:.3f})"
    return None
