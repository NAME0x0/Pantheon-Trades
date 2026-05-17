"""USYC treasury — park idle paper-trade bankroll in a yield-bearing
tokenised money-market fund.

USYC is Circle's tokenized money market fund (ERC-20 on supported
chains). When the council is between trades, idle USDC bankroll
sitting on the wallet earns 0%. Parking it in USYC earns whatever the
fund's published yield is — small, but mechanical, and the rebate /
fee path is unaffected.

This module is a thin accounting + intent layer. The actual mint /
redeem flow on Arc uses Circle's USYC contracts — we wrap the
operator-facing decisions:

  * ``parked_amount(book)`` — how much of the book's idle balance is
    eligible to park, given a minimum unallocated floor.
  * ``daily_accrual(amount, yield_bps)`` — naive yield projection so an
    operator can see the expected drip.
  * ``project_treasury_revenue(...)`` — back-of-envelope annual yield
    given expected idle balance.

The intent-side helpers ``mint_intent`` / ``redeem_intent`` produce a
serialisable record an upstream bot / API can consume to actually fire
the on-chain mint / redeem. We keep network I/O out of this module so
it stays unit-testable.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

# Defaults align with USYC's published yield range. Operator overrides.
DEFAULT_YIELD_BPS = float(os.environ.get("USYC_ANNUAL_YIELD_BPS", "500"))  # 5.00% APY
DEFAULT_MIN_UNALLOCATED = float(os.environ.get("USYC_MIN_UNALLOCATED_USDC", "100"))


@dataclass(frozen=True)
class TreasuryIntent:
    """Operator-readable intent — what the treasury wants to do next.

    The upstream LiveExecutor / on-chain submitter is responsible for
    actually firing the corresponding USYC mint / redeem transaction.
    """

    action: Literal["mint", "redeem", "hold"]
    amount_usdc: float
    reason: str
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TreasuryState:
    """Mutable view of the parking layer."""

    book_usdc: float
    parked_usdc: float = 0.0
    yield_bps: float = DEFAULT_YIELD_BPS
    min_unallocated_usdc: float = DEFAULT_MIN_UNALLOCATED

    @property
    def idle_usdc(self) -> float:
        """USDC available on the wallet (not in USYC, not committed)."""
        return max(0.0, self.book_usdc - self.parked_usdc)

    def mint_intent(self) -> TreasuryIntent:
        """How much of idle should be moved into USYC right now?

        Conservatively leaves ``min_unallocated_usdc`` on the wallet so
        gas + small trades don't trigger a redeem cycle every tick.
        Returns ``hold`` when nothing to park.
        """
        candidate = self.idle_usdc - self.min_unallocated_usdc
        if candidate <= 0:
            return TreasuryIntent(
                action="hold",
                amount_usdc=0.0,
                reason=f"idle {self.idle_usdc:.2f} <= floor {self.min_unallocated_usdc:.2f}",
            )
        return TreasuryIntent(
            action="mint",
            amount_usdc=candidate,
            reason=f"park {candidate:.2f} of idle {self.idle_usdc:.2f} above floor",
        )

    def redeem_intent(self, needed_usdc: float) -> TreasuryIntent:
        """How much of the parked balance needs to be redeemed to cover
        a pending trade of ``needed_usdc``?

        Idle covers the first slice; the rest is redeemed from USYC.
        """
        shortfall = max(0.0, needed_usdc - self.idle_usdc)
        if shortfall <= 0:
            return TreasuryIntent(
                action="hold",
                amount_usdc=0.0,
                reason=f"idle {self.idle_usdc:.2f} covers needed {needed_usdc:.2f}",
            )
        amount = min(self.parked_usdc, shortfall)
        return TreasuryIntent(
            action="redeem",
            amount_usdc=amount,
            reason=f"redeem {amount:.2f} from parked {self.parked_usdc:.2f} for trade",
        )

    def apply_mint(self, amount_usdc: float) -> None:
        """Record a confirmed mint. Caller fires the on-chain tx; we
        update the parking ledger when it's confirmed."""
        if amount_usdc < 0:
            raise ValueError("mint amount must be non-negative")
        cap = self.idle_usdc
        actual = min(amount_usdc, cap)
        self.parked_usdc += actual

    def apply_redeem(self, amount_usdc: float) -> None:
        """Record a confirmed redeem."""
        if amount_usdc < 0:
            raise ValueError("redeem amount must be non-negative")
        actual = min(amount_usdc, self.parked_usdc)
        self.parked_usdc -= actual


def daily_accrual(amount_usdc: float, yield_bps: float = DEFAULT_YIELD_BPS) -> float:
    """Naive daily USDC accrual on a parked balance.

    Yield is annualised — we divide by 365 for the daily drip. USYC
    publishes its own rate; this helper is for sizing expectations
    only, not for accruing on-chain.
    """
    if amount_usdc <= 0 or yield_bps <= 0:
        return 0.0
    return amount_usdc * (yield_bps / 10_000.0) / 365.0


def project_treasury_revenue(
    *,
    expected_idle_usdc: float,
    yield_bps: float = DEFAULT_YIELD_BPS,
    days: int = 365,
) -> dict[str, float]:
    """Project total yield earned over ``days`` at a steady idle level.

    For an agent with $10k bankroll trading lightly, this routinely
    adds $30-60/month of risk-free yield — material against the LLM
    bill, immaterial against the trading edge.
    """
    daily = daily_accrual(expected_idle_usdc, yield_bps)
    total = daily * days
    return {
        "expected_idle_usdc": expected_idle_usdc,
        "yield_bps": yield_bps,
        "days": days,
        "daily_accrual_usdc": daily,
        "total_accrual_usdc": total,
        "effective_apy": yield_bps / 10_000.0,
    }


def intent_to_json(intent: TreasuryIntent) -> dict:
    return asdict(intent)
