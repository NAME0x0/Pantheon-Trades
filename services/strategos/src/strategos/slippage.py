"""Slippage estimation for prediction-market orders.

For an order of ``size_usdc`` against a book with ``depth_usdc`` of standing
liquidity near the mid, we approximate slippage as a fraction of the order
relative to depth, capped at ``MAX_SLIPPAGE``. The model is intentionally
simple; an exchange-specific override can be plugged in by callers.
"""

from __future__ import annotations


MAX_SLIPPAGE = 0.05  # 5pp absolute, hard cap
LINEAR_SLOPE = 0.20
MIN_DEPTH_USDC = 1.0


def estimate_slippage(size_usdc: float, depth_usdc: float) -> float:
    """Return expected slippage in absolute price units (e.g. 0.012 = 1.2pp)."""
    if size_usdc <= 0:
        return 0.0
    depth = max(depth_usdc, MIN_DEPTH_USDC)
    fraction = size_usdc / depth
    return min(LINEAR_SLOPE * fraction, MAX_SLIPPAGE)


def slippage_eats_edge(size_usdc: float, depth_usdc: float, edge: float) -> bool:
    """True if expected slippage consumes more than half of the edge."""
    return estimate_slippage(size_usdc, depth_usdc) >= 0.5 * abs(edge)
