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

# Polymarket Fee Structure V2 (March 30 2026). Source:
# https://help.polymarket.com/en/articles/13364478-trading-fees
# Values are *peak* nominal taker fees in basis points at p=0.50; the
# actual realised fee scales with the price-from-0.50 distance — we use
# the peak for conservative sizing-side accounting.
TAKER_FEE_BPS_BY_CATEGORY = {
    "crypto": 720,
    "sports": 300,
    "finance": 400,
    "politics": 400,
    "tech": 400,
    "economics": 500,
    "culture": 500,
    "weather": 500,
    "geopolitics": 0,        # fee-free per Polymarket V2
    "world_events": 0,       # fee-free
    "other": 500,
}
# Maker rebate share of taker fee. The protocol redistributes 20-25%
# of collected fees daily; using 22% as the midpoint for accounting.
MAKER_REBATE_SHARE = 0.22


@dataclass(frozen=True)
class ExecutionDecision:
    mode: Mode
    limit_price: float  # absolute side price to post at, in [0.01, 0.99]
    reason: str
    # `post_only` is the Polymarket CLOB v2 flag that rejects an order
    # at exchange-side if it would cross the book (and thus take rather
    # than make). Mandatory for maker-rebate eligibility on rewarded
    # markets — see docs/FEES_AND_EDGE.md. Always True when mode=maker,
    # always False for taker. Kept as an explicit field so the live
    # router can pass it straight through without inspecting `mode`.
    post_only: bool = False
    # Polymarket category determines fee rate (and rebate rate). When
    # the category is "geopolitics" or "world events" the fee is zero
    # and rebates are zero; we still record `post_only=True` for maker
    # decisions because it's cheap insurance against accidental crosses.
    expected_taker_fee_bps: float | None = None
    expected_maker_rebate_bps: float | None = None


def choose_execution(
    side_price: float,
    *,
    edge_abs: float,
    depth_usdc: float,
    size_usdc: float,
    days_to_resolution: float | None = None,
    category: str | None = None,
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

    cat_key = (category or "other").lower()
    taker_fee_bps = float(TAKER_FEE_BPS_BY_CATEGORY.get(cat_key, TAKER_FEE_BPS_BY_CATEGORY["other"]))
    rebate_bps = taker_fee_bps * MAKER_REBATE_SHARE

    def _taker(reason: str) -> ExecutionDecision:
        return ExecutionDecision(
            mode="taker",
            limit_price=taker_price,
            reason=reason,
            post_only=False,
            expected_taker_fee_bps=taker_fee_bps,
            expected_maker_rebate_bps=0.0,
        )

    if days_to_resolution is not None and days_to_resolution < min_days_for_maker:
        return _taker(f"urgent: {days_to_resolution:.1f}d < {min_days_for_maker}d")
    if edge_abs >= maker_max_edge:
        return _taker(f"high conviction: |edge| {edge_abs:.3f} >= {maker_max_edge}")
    if depth_usdc <= 0 or size_usdc / depth_usdc > maker_max_size_depth_ratio:
        return _taker(
            f"size/depth too large: {size_usdc:.0f}/{depth_usdc:.0f} "
            f"> {maker_max_size_depth_ratio}"
        )
    # Degenerate prices — can't post a meaningful maker quote near the edges.
    if maker_price <= 0.01 or maker_price >= 0.99:
        return _taker("side price at unit edge; maker quote would be invalid")
    return ExecutionDecision(
        mode="maker",
        limit_price=maker_price,
        reason=(
            f"maker eligible: |edge|={edge_abs:.3f}, "
            f"size/depth={size_usdc / depth_usdc:.3f}, "
            f"category={cat_key}, fee_bps={taker_fee_bps:.0f}, rebate_bps={rebate_bps:.0f}"
        ),
        # Always set post_only=True for maker orders so the Polymarket
        # CLOB v2 exchange rejects (rather than crosses) if a taker
        # snipes the spread before our order rests. This is the *only*
        # way to guarantee maker-rebate eligibility on a fill.
        post_only=True,
        expected_taker_fee_bps=0.0,
        expected_maker_rebate_bps=rebate_bps,
    )


def _clip_unit(x: float) -> float:
    return max(0.01, min(0.99, x))
