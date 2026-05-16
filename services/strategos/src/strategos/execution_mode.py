"""Pick maker vs taker per order, with a price suggestion.

The taker path (current default) crosses the spread: limit price is
``side_price + slippage_estimate``, so the order fills immediately
against resting depth. We pay the spread and the slippage curve.

The maker path posts *inside* the spread by a small epsilon: limit
price is ``side_price - maker_epsilon`` (we are always buying — selling
mechanics flip the sign). The CLOB earns us a maker rebate on fills,
but the fill is not guaranteed and may sit on the book until the
market moves to us or we cancel.

The heuristic is deliberately conservative — we only switch to maker
when *all* of the following hold:

  - The order is not urgent (``days_to_resolution`` is None or ≥
    ``MIN_DAYS_FOR_MAKER``).
  - Edge is moderate, not extreme. Strong conviction prefers fills
    over rebates: missing a 30pp edge to save 1bp rebate is bad.
  - The order is small relative to depth — otherwise it sits there
    waiting and we never get out of the price we wanted.

If any check fails, we fall back to taker. That preserves the existing
fill behaviour as the safe default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from strategos.slippage import estimate_slippage

Mode = Literal["maker", "taker"]

# Conservative defaults — tuned by the operator over time, not magic numbers.
MAKER_EPSILON = 0.005          # post 0.5pp inside the spread on BUY
MAKER_MAX_EDGE = 0.20          # high conviction always crosses
MAKER_MAX_SIZE_DEPTH_RATIO = 0.10  # order >10% of depth = unlikely to rest
MIN_DAYS_FOR_MAKER = 5.0


@dataclass(frozen=True)
class ExecutionDecision:
    mode: Mode
    limit_price: float  # absolute side price to post at, in [0.01, 0.99]
    reason: str


def choose_execution(
    side_price: float,
    *,
    edge_abs: float,
    depth_usdc: float,
    size_usdc: float,
    days_to_resolution: float | None = None,
    maker_epsilon: float = MAKER_EPSILON,
    maker_max_edge: float = MAKER_MAX_EDGE,
    maker_max_size_depth_ratio: float = MAKER_MAX_SIZE_DEPTH_RATIO,
    min_days_for_maker: float = MIN_DAYS_FOR_MAKER,
) -> ExecutionDecision:
    """Return mode + limit price for a BUY at ``side_price`` on our side.

    Falls back to taker on every failed maker condition — there is no
    safe path that posts a fill-or-rest order at any price; the cost
    of a missed fill is asymmetric.
    """
    slip = estimate_slippage(size_usdc, depth_usdc)
    taker_price = _clip_unit(side_price + slip)
    maker_price = _clip_unit(side_price - maker_epsilon)

    if days_to_resolution is not None and days_to_resolution < min_days_for_maker:
        return ExecutionDecision(
            mode="taker",
            limit_price=taker_price,
            reason=f"urgent: {days_to_resolution:.1f}d < {min_days_for_maker}d",
        )
    if edge_abs >= maker_max_edge:
        return ExecutionDecision(
            mode="taker",
            limit_price=taker_price,
            reason=f"high conviction: |edge| {edge_abs:.3f} >= {maker_max_edge}",
        )
    if depth_usdc <= 0 or size_usdc / depth_usdc > maker_max_size_depth_ratio:
        return ExecutionDecision(
            mode="taker",
            limit_price=taker_price,
            reason=(
                f"size/depth too large: {size_usdc:.0f}/{depth_usdc:.0f} "
                f"> {maker_max_size_depth_ratio}"
            ),
        )
    # Degenerate prices — can't post a meaningful maker quote near the edges.
    if maker_price <= 0.01 or maker_price >= 0.99:
        return ExecutionDecision(
            mode="taker",
            limit_price=taker_price,
            reason="side price at unit edge; maker quote would be invalid",
        )
    return ExecutionDecision(
        mode="maker",
        limit_price=maker_price,
        reason=(
            f"maker eligible: |edge|={edge_abs:.3f}, "
            f"size/depth={size_usdc / depth_usdc:.3f}"
        ),
    )


def _clip_unit(x: float) -> float:
    return max(0.01, min(0.99, x))
