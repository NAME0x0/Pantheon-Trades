"""Order payload helpers — convert a TradeIntent into the CLOB OrderRequest."""

from __future__ import annotations

from strategos.intent import TradeIntent
from strategos.polymarket_clob import OrderRequest
from strategos.slippage import estimate_slippage


def build_order_request(
    intent: TradeIntent,
    *,
    depth_usdc: float,
    max_slippage: float = 0.05,
) -> OrderRequest | None:
    if intent.selected_token_id is None:
        return None
    slippage = min(max_slippage, estimate_slippage(intent.size_usdc, depth_usdc))
    limit_price = max(0.01, min(0.99, intent.side_price + slippage))
    return OrderRequest(
        token_id=intent.selected_token_id,
        side="BUY",
        price=round(limit_price, 3),
        size=round(intent.contracts, 4),
    )
