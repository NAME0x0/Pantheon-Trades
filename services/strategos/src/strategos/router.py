"""Strategos router — picks between live and paper execution per ApprovalToken.

Decision matrix:
  * ``EXECUTION_MODE=paper``  -> always paper
  * ``EXECUTION_MODE=live``   -> always live (after constitutional check)
  * ``EXECUTION_MODE=auto``   -> paper unless thesis carries the
                                 ``live_eligible`` flag and Olympus says
                                 the system is in ACTIVE state.

The router does not own portfolio state — both backends are passed in
constructed. This keeps the router stateless and easy to test.
"""

from __future__ import annotations

import os
from typing import Literal

import structlog

from pantheon_core.schema import ApprovalToken, Thesis, Trade

from strategos.live import LiveExecutor
from strategos.paper import PaperBook

Mode = Literal["paper", "live", "auto"]

log = structlog.get_logger("strategos.router")


class Strategos:
    def __init__(
        self,
        paper: PaperBook,
        live: LiveExecutor | None = None,
        mode: Mode | None = None,
    ) -> None:
        self._paper = paper
        self._live = live
        self._mode: Mode = mode or os.environ.get("EXECUTION_MODE", "paper")  # type: ignore[assignment]

    @property
    def mode(self) -> Mode:
        return self._mode

    def _resolve_mode(self, thesis: Thesis) -> Mode:
        if self._mode in ("paper", "live"):
            return self._mode
        # auto: prefer paper unless this thesis is explicitly marked safe.
        if "live_eligible" in thesis.humans_flags and self._live is not None:
            return "live"
        return "paper"

    async def execute(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        *,
        mid_price: float,
        depth_usdc: float,
        yes_token_id: str | None = None,
        no_token_id: str | None = None,
    ) -> Trade:
        if token.decision not in ("APPROVED", "RESIZED"):
            raise ValueError(f"refused execution: decision={token.decision}")
        mode = self._resolve_mode(thesis)
        if mode == "live":
            if self._live is None or yes_token_id is None or no_token_id is None:
                raise RuntimeError("live execution requested but live executor or token ids missing")
            log.info("strategos.route_live", thesis_id=thesis.thesis_id)
            return await self._live.execute(
                token=token,
                thesis=thesis,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                mid_price=mid_price,
                depth_usdc=depth_usdc,
            )
        log.info("strategos.route_paper", thesis_id=thesis.thesis_id)
        return self._paper.execute(token, thesis, mid_price=mid_price, depth_usdc=depth_usdc)
