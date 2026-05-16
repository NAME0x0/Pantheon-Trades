"""Live trade execution — routes ApprovalTokens to the Polymarket CLOB.

Single responsibility: turn an ``ApprovalToken`` + ``Thesis`` into a signed
order, submit it, and emit a ``Trade`` record. Position monitoring is
delegated to Argos; settlement is delegated to ``settlement_watcher``.

Hard rules enforced here:
  * Never trade without an ApprovalToken (constitution).
  * Never submit if slippage would eat more than half the edge.
  * Never exceed ``size_pct * portfolio_usdc`` notional.
"""

from __future__ import annotations

import structlog

from pantheon_core.direction import entry_price as direction_entry_price
from pantheon_core.schema import ApprovalToken, Thesis, Trade, utc_now

from strategos.execution_mode import choose_execution
from strategos.polymarket_clob import OrderRequest, OrderResponse, PolymarketClobClient
from strategos.slippage import slippage_eats_edge
from strategos.slippage_learner import SlippageLearner

log = structlog.get_logger("strategos.live")


class LiveExecutor:
    def __init__(
        self,
        clob: PolymarketClobClient,
        portfolio_usdc: float,
        slippage_learner: SlippageLearner | None = None,
    ) -> None:
        self._clob = clob
        self._portfolio_usdc = portfolio_usdc
        self._learner = slippage_learner

    @property
    def slippage_learner(self) -> SlippageLearner | None:
        return self._learner

    @property
    def portfolio_usdc(self) -> float:
        return self._portfolio_usdc

    def update_portfolio(self, new_value: float) -> None:
        if new_value < 0:
            raise ValueError("portfolio value cannot be negative")
        self._portfolio_usdc = new_value

    async def execute(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        yes_token_id: str,
        no_token_id: str,
        mid_price: float,
        depth_usdc: float,
    ) -> Trade:
        if token.decision not in ("APPROVED", "RESIZED"):
            raise ValueError(f"refused execution: token decision={token.decision}")

        size_pct = token.final_size_pct or 0.0
        size_usdc = size_pct * self._portfolio_usdc
        side_price = direction_entry_price(mid_price, thesis.direction)

        # Refuse to trade when slippage swallows the alpha.
        if slippage_eats_edge(size_usdc, depth_usdc, thesis.signed_edge):
            log.warning(
                "strategos.refused_for_slippage",
                thesis_id=thesis.thesis_id,
                size_usdc=size_usdc,
                depth_usdc=depth_usdc,
            )
            return Trade(
                thesis_id=token.thesis_id,
                market_id=thesis.market_id,
                direction=thesis.direction,
                size_pct=size_pct,
                size_usdc=size_usdc,
                entry_price=side_price,
                status="cancelled",
                fill_time=utc_now(),
            )

        token_id = yes_token_id if thesis.direction == "YES" else no_token_id
        decision = choose_execution(
            side_price,
            edge_abs=abs(thesis.signed_edge),
            depth_usdc=depth_usdc,
            size_usdc=size_usdc,
            days_to_resolution=getattr(thesis, "days_to_resolution", None),
        )
        limit_price = decision.limit_price
        log.info(
            "strategos.execution_mode",
            thesis_id=thesis.thesis_id,
            mode=decision.mode,
            limit_price=limit_price,
            reason=decision.reason,
        )
        # Polymarket orders are denominated in contracts. One contract pays $1 on resolution.
        contracts = size_usdc / limit_price if limit_price > 0 else 0.0

        req = OrderRequest(
            token_id=token_id,
            side="BUY",
            price=round(limit_price, 3),
            size=round(contracts, 4),
        )
        try:
            resp: OrderResponse = await self._clob.submit(req)
        except Exception as e:
            log.exception("strategos.clob_submit_failed", thesis_id=thesis.thesis_id, error=str(e))
            return Trade(
                thesis_id=token.thesis_id,
                market_id=thesis.market_id,
                direction=thesis.direction,
                size_pct=size_pct,
                size_usdc=size_usdc,
                entry_price=side_price,
                status="failed",
                fill_time=utc_now(),
            )

        status = "filled" if resp.filled_size and resp.filled_size >= contracts * 0.99 else (
            "partial" if resp.filled_size > 0 else "pending"
        )

        # Fold the realised slippage back into the learner so the next
        # order on this market sees a refined estimate. We define
        # realised slippage as ``max(0, avg_fill - side_price)`` for a
        # BUY — i.e. how much worse than the quoted side we filled.
        if (
            self._learner is not None
            and resp.avg_price is not None
            and resp.filled_size
            and resp.filled_size > 0
        ):
            actual = max(0.0, float(resp.avg_price) - side_price)
            try:
                self._learner.observe(
                    market_id=thesis.market_id,
                    actual_slippage=actual,
                    size_usdc=size_usdc,
                    depth_usdc=depth_usdc,
                )
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "strategos.learner_observe_failed",
                    thesis_id=thesis.thesis_id,
                    error=str(e),
                )

        return Trade(
            thesis_id=token.thesis_id,
            market_id=thesis.market_id,
            direction=thesis.direction,
            size_pct=size_pct,
            size_usdc=size_usdc,
            entry_price=side_price,
            status=status,  # type: ignore[arg-type]
            order_id=resp.order_id,
            fill_price=resp.avg_price,
            fill_time=utc_now(),
        )
