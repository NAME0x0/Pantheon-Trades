"""Order-book imbalance feature.

Quality features (liquidity, spread, etc.) tell you a market is
*tradeable*. Predictive features tell you *which way to bet*. Order-
book imbalance is one of the most reliable predictive features in
short-horizon market microstructure literature: a heavy bid side
relative to ask side precedes upward price moves on a horizon
proportional to depth refresh.

We compute a depth-weighted skew score in [-1, +1]:

    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

Positive → bid-heavy → upward pressure → probability nudge UP.
Negative → ask-heavy → downward pressure → probability nudge DOWN.

The book-side depths are typically passed in as the cumulative size
within ``N pp`` of the inside quote (e.g. all bids within 3pp of the
best bid). Levels deeper than that contribute noise.

Returns an additive probability delta in roughly [-0.04, +0.04].
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_DELTA = 0.04


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    size_usdc: float


def _depth_within(levels: list[OrderBookLevel], inside: float, window_pp: float) -> float:
    """Cumulative USDC size whose price is within ``window_pp`` of ``inside``."""
    if window_pp <= 0:
        return 0.0
    lo = inside - window_pp
    hi = inside + window_pp
    return float(sum(lvl.size_usdc for lvl in levels if lo <= lvl.price <= hi and lvl.size_usdc > 0))


def orderbook_imbalance(
    bids: list[OrderBookLevel],
    asks: list[OrderBookLevel],
    *,
    window_pp: float = 0.03,
) -> float:
    """Raw imbalance in [-1, +1]. 0 = perfectly balanced book."""
    if not bids or not asks:
        return 0.0
    best_bid = max(lvl.price for lvl in bids)
    best_ask = min(lvl.price for lvl in asks)
    bid_depth = _depth_within(bids, best_bid, window_pp)
    ask_depth = _depth_within(asks, best_ask, window_pp)
    total = bid_depth + ask_depth
    if total <= 0:
        return 0.0
    return (bid_depth - ask_depth) / total


def imbalance_probability_delta(
    bids: list[OrderBookLevel],
    asks: list[OrderBookLevel],
    *,
    window_pp: float = 0.03,
    scale: float = MAX_DELTA,
) -> float:
    """Additive probability adjustment ready for ``oracle_probability``.

    Imbalance is clipped before scaling so extreme one-sided books
    cannot push the oracle probability arbitrarily far. ``scale`` is
    the maximum absolute delta this feature can contribute.
    """
    raw = orderbook_imbalance(bids, asks, window_pp=window_pp)
    raw = max(-1.0, min(1.0, raw))
    return raw * scale
