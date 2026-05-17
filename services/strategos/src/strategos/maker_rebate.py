"""Maker-rebate accounting for Polymarket CLOB v2.

Polymarket V2 (March 30 2026) introduced taker fees + maker rebates.
The protocol skims 20-25% of each collected taker fee and redistributes
it daily in USDC to liquidity providers. We model the midpoint (22%)
of the published 20-25% range.

This module is a *pure accounting layer*. It does **not** submit orders.
It books, per trade:

  * Cash fee paid (taker) — negative PnL contribution.
  * Cash rebate accrued (maker, post-fill) — positive PnL contribution.
  * Net effective fee bps after rebate.

The intent is to give Ostrakon a truthful per-trade fee record so the
Brier-vs-PnL correlation is computed against *after-fee* outcomes, not
the headline taker rate. Without this, every paper PnL will overstate
the cost of patient maker flow.

See ``docs/FEES_AND_EDGE.md`` for the full V2 fee schedule + sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Same table as strategos.execution_mode. Re-imported here to keep the
# accounting module self-contained — operators sometimes run rebate
# audits without the execution-mode module loaded (e.g. from a notebook).
TAKER_FEE_BPS_BY_CATEGORY = {
    "crypto": 720,
    "sports": 300,
    "finance": 400,
    "politics": 400,
    "tech": 400,
    "economics": 500,
    "culture": 500,
    "weather": 500,
    "geopolitics": 0,
    "world_events": 0,
    "other": 500,
}
MAKER_REBATE_SHARE = 0.22

Mode = Literal["maker", "taker"]


@dataclass
class FeeBooking:
    """One row of fee accounting per executed trade.

    Attributes:
        trade_id: trade identifier (matches ``Trade.trade_id``).
        market_id: market identifier.
        category: Polymarket category as it appears in the V2 schedule.
        mode: ``"maker"`` or ``"taker"`` — drives whether fee was paid
              or rebate accrued.
        notional_usdc: size in USDC the fee/rebate is computed against.
        nominal_fee_bps: the peak (p=0.50) nominal taker fee for the
              category. Stored even on maker trades so an operator can
              see "what would I have paid as taker".
        fee_paid_usdc: cash fee actually paid (always 0 on maker).
        rebate_accrued_usdc: cash rebate (always 0 on taker).
        effective_bps: realised net effective fee in bps. Negative
              numbers mean we earned more rebate than fee. Always
              compared against the trade's ``notional_usdc``.
    """

    trade_id: str
    market_id: str
    category: str
    mode: Mode
    notional_usdc: float
    nominal_fee_bps: float
    fee_paid_usdc: float
    rebate_accrued_usdc: float
    effective_bps: float


@dataclass
class FeeLedger:
    """Append-only ledger of all fee bookings.

    Trade execution calls ``book(...)``; reports read ``rows``,
    ``totals()``, or ``by_category()``. Designed to be JSON-serialised
    and replayed against Ostrakon for after-fee PnL attribution.
    """

    rows: list[FeeBooking] = field(default_factory=list)

    def book(
        self,
        *,
        trade_id: str,
        market_id: str,
        category: str | None,
        mode: Mode,
        notional_usdc: float,
        rebate_share: float = MAKER_REBATE_SHARE,
    ) -> FeeBooking:
        """Compute and record fee/rebate for a fill. Returns the row."""
        cat_key = (category or "other").lower()
        nominal_bps = float(TAKER_FEE_BPS_BY_CATEGORY.get(cat_key, TAKER_FEE_BPS_BY_CATEGORY["other"]))
        notional = max(0.0, float(notional_usdc))

        if mode == "taker":
            fee = notional * nominal_bps / 10_000.0
            rebate = 0.0
            eff_bps = nominal_bps
        elif mode == "maker":
            fee = 0.0
            rebate = notional * nominal_bps * rebate_share / 10_000.0
            # Effective is negative — rebate earned, no fee paid.
            eff_bps = -nominal_bps * rebate_share
        else:
            raise ValueError(f"unknown execution mode: {mode}")

        row = FeeBooking(
            trade_id=trade_id,
            market_id=market_id,
            category=cat_key,
            mode=mode,
            notional_usdc=notional,
            nominal_fee_bps=nominal_bps,
            fee_paid_usdc=fee,
            rebate_accrued_usdc=rebate,
            effective_bps=eff_bps,
        )
        self.rows.append(row)
        return row

    def totals(self) -> dict[str, float]:
        """Aggregate fees vs rebates across the entire ledger."""
        total_fees = sum(r.fee_paid_usdc for r in self.rows)
        total_rebates = sum(r.rebate_accrued_usdc for r in self.rows)
        total_notional = sum(r.notional_usdc for r in self.rows)
        net_cost = total_fees - total_rebates
        return {
            "trades": float(len(self.rows)),
            "notional_usdc": total_notional,
            "fees_paid_usdc": total_fees,
            "rebates_accrued_usdc": total_rebates,
            "net_cost_usdc": net_cost,
            "net_bps": (net_cost / total_notional * 10_000) if total_notional > 0 else 0.0,
        }

    def by_category(self) -> dict[str, dict[str, float]]:
        """Per-category breakdown — useful for diagnosing which markets
        the LP-side flow is actually paying for."""
        out: dict[str, dict[str, float]] = {}
        for r in self.rows:
            agg = out.setdefault(
                r.category,
                {"trades": 0.0, "notional_usdc": 0.0, "fees_paid_usdc": 0.0,
                 "rebates_accrued_usdc": 0.0},
            )
            agg["trades"] += 1
            agg["notional_usdc"] += r.notional_usdc
            agg["fees_paid_usdc"] += r.fee_paid_usdc
            agg["rebates_accrued_usdc"] += r.rebate_accrued_usdc
        return out


def project_savings(
    *,
    n_trades_per_day: float,
    avg_notional_usdc: float,
    maker_share: float,
    category: str = "other",
) -> dict[str, float]:
    """Back-of-envelope: what does flipping the maker share buy you?

    Useful for the operator deciding whether the work of going maker-
    biased is worth it for a given expected volume.
    """
    cat = TAKER_FEE_BPS_BY_CATEGORY.get(category.lower(), TAKER_FEE_BPS_BY_CATEGORY["other"])
    daily_notional = n_trades_per_day * avg_notional_usdc
    annual_notional = daily_notional * 365

    # Round-trip cost in bps under each policy.
    all_taker_bps = 2 * cat                         # entry + exit at full taker
    maker_taker_mix_bps = (
        (1 - maker_share) * 2 * cat                 # pure-taker fraction
        + maker_share * (cat - cat * MAKER_REBATE_SHARE)  # maker entry + taker exit
    )

    annual_all_taker = annual_notional * all_taker_bps / 10_000.0
    annual_mix = annual_notional * maker_taker_mix_bps / 10_000.0
    savings = annual_all_taker - annual_mix

    return {
        "category": category,
        "annual_notional_usdc": annual_notional,
        "annual_cost_all_taker_usdc": annual_all_taker,
        "annual_cost_mixed_usdc": annual_mix,
        "annual_savings_usdc": savings,
        "bps_saved_per_round_trip": all_taker_bps - maker_taker_mix_bps,
    }
