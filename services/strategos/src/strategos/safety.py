"""Live-mode safety wrapper.

When ``EXECUTION_MODE=live`` we route real orders. Before that ever
happens we want hard guarantees:

  * **Circuit breaker** — after ``MAX_CONSECUTIVE_LOSSES`` consecutive
    losing settlements we flip back to paper mode automatically.
  * **First-N approval** — the first ``REQUIRE_MANUAL_FIRST_N`` live
    trades demand a human flag (``STRATEGOS_LIVE_APPROVED=1``) before
    submission. Prevents accidental live mode on a fresh deploy.
  * **Daily cost cap** — cumulative LLM + chain spend is tracked in
    Redis (``strategos:cost:usd:day:YYYY-MM-DD``). Crossing the
    threshold halts live execution for the rest of the UTC day.
  * **Quote-time edge re-check** — before submit, re-evaluate the
    market's current ask vs the Apollo signal's recorded ask. If the
    inside has moved against us by more than ``MAX_QUOTE_DRIFT``,
    abort and emit a restraint candidate.

Wire this around the Strategos live router by calling
``await SafetyWrapper.guard(token, thesis, current_book)`` before
submitting. Returns ``GuardDecision.PROCEED`` or one of the abort
reasons; the router then publishes a RejectionRecord and lets
Areopagus anchor the restraint on chain if appropriate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import ApprovalToken, Thesis

log = structlog.get_logger("strategos.safety")

MAX_CONSECUTIVE_LOSSES = int(os.environ.get("STRATEGOS_MAX_CONSECUTIVE_LOSSES", "3"))
REQUIRE_MANUAL_FIRST_N = int(os.environ.get("STRATEGOS_REQUIRE_MANUAL_FIRST_N", "5"))
MAX_QUOTE_DRIFT = float(os.environ.get("STRATEGOS_MAX_QUOTE_DRIFT", "0.03"))
DAILY_COST_CAP_USD = float(os.environ.get("STRATEGOS_DAILY_COST_CAP_USD", "25.0"))

CONSEC_LOSSES_KEY = "strategos:safety:consec_losses"
LIVE_TRADE_COUNT_KEY = "strategos:safety:live_trade_count"
COST_KEY_FMT = "strategos:cost:usd:day:{day}"
APPROVED_FLAG_ENV = "STRATEGOS_LIVE_APPROVED"


class GuardDecision(str, Enum):
    PROCEED = "PROCEED"
    PAPER_FALLBACK = "PAPER_FALLBACK"          # auto-flip back to paper
    AWAIT_MANUAL = "AWAIT_MANUAL"              # first-N approval missing
    COST_CAP_EXCEEDED = "COST_CAP_EXCEEDED"    # over daily $ budget
    QUOTE_DRIFT_ABORT = "QUOTE_DRIFT_ABORT"    # market moved at submit time


@dataclass
class GuardResult:
    decision: GuardDecision
    reason: str
    detail: dict


class SafetyWrapper:
    """Stateful gate around live submission. State lives in Redis so
    multiple Strategos workers see the same circuit-breaker view."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    # ── Hooks called from settlement / cost emitter ───────────────────

    async def record_settlement(self, pnl_usdc: float) -> None:
        """Update the consecutive-losses counter at settlement time."""
        if pnl_usdc < 0:
            await self._redis.incr(CONSEC_LOSSES_KEY)
        else:
            await self._redis.set(CONSEC_LOSSES_KEY, "0")

    async def record_cost(self, usd: float) -> None:
        """Bump today's cumulative LLM + chain + fee spend."""
        if usd <= 0:
            return
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = COST_KEY_FMT.format(day=day)
        # INCRBYFLOAT is exactly the right shape.
        await self._redis.incrbyfloat(key, usd)
        await self._redis.expire(key, 7 * 24 * 3600)

    async def record_live_trade(self) -> int:
        """Increment the lifetime live-trade counter; returns new total."""
        return int(await self._redis.incr(LIVE_TRADE_COUNT_KEY))

    # ── Single pre-trade gate ────────────────────────────────────────

    async def guard(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        *,
        current_ask: Optional[float] = None,
        recorded_ask: Optional[float] = None,
    ) -> GuardResult:
        # 1. circuit breaker on consecutive losses
        consec = int((await self._redis.get(CONSEC_LOSSES_KEY)) or 0)
        if consec >= MAX_CONSECUTIVE_LOSSES:
            log.warning(
                "strategos.safety.circuit_breaker",
                consec_losses=consec,
                cap=MAX_CONSECUTIVE_LOSSES,
            )
            return GuardResult(
                decision=GuardDecision.PAPER_FALLBACK,
                reason="CIRCUIT_BREAKER",
                detail={"consecutive_losses": consec},
            )

        # 2. daily cost cap
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cost_today = float((await self._redis.get(COST_KEY_FMT.format(day=day))) or 0.0)
        if cost_today >= DAILY_COST_CAP_USD:
            log.warning(
                "strategos.safety.cost_cap",
                spent_usd=cost_today,
                cap_usd=DAILY_COST_CAP_USD,
            )
            return GuardResult(
                decision=GuardDecision.COST_CAP_EXCEEDED,
                reason="DAILY_COST_CAP",
                detail={"spent_usd": cost_today, "cap_usd": DAILY_COST_CAP_USD},
            )

        # 3. first-N manual approval
        live_n = int((await self._redis.get(LIVE_TRADE_COUNT_KEY)) or 0)
        if live_n < REQUIRE_MANUAL_FIRST_N:
            approved = os.environ.get(APPROVED_FLAG_ENV, "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            if not approved:
                log.info(
                    "strategos.safety.first_n_block",
                    live_n=live_n,
                    require_first_n=REQUIRE_MANUAL_FIRST_N,
                    env_var=APPROVED_FLAG_ENV,
                )
                return GuardResult(
                    decision=GuardDecision.AWAIT_MANUAL,
                    reason="FIRST_N_MANUAL_APPROVAL_REQUIRED",
                    detail={
                        "live_trades_so_far": live_n,
                        "require_first_n": REQUIRE_MANUAL_FIRST_N,
                    },
                )

        # 4. quote-time edge re-check
        if current_ask is not None and recorded_ask is not None:
            drift = abs(current_ask - recorded_ask)
            if drift > MAX_QUOTE_DRIFT:
                log.info(
                    "strategos.safety.quote_drift_abort",
                    drift=round(drift, 4),
                    cap=MAX_QUOTE_DRIFT,
                    recorded_ask=recorded_ask,
                    current_ask=current_ask,
                )
                return GuardResult(
                    decision=GuardDecision.QUOTE_DRIFT_ABORT,
                    reason="QUOTE_DRIFT",
                    detail={
                        "recorded_ask": recorded_ask,
                        "current_ask": current_ask,
                        "drift": drift,
                        "max_drift": MAX_QUOTE_DRIFT,
                    },
                )

        return GuardResult(
            decision=GuardDecision.PROCEED,
            reason="OK",
            detail={"live_trades_so_far": live_n, "consec_losses": consec, "spent_usd_today": cost_today},
        )
