"""Polymarket V2 builder-code attribution.

Polymarket's V2 spec (April 2026) introduced *builder codes* — a per-
fill attribution mechanism that pays USDC builder fees to the agent /
service that originated the trade recommendation, with no custody and
no separate token. Reference:
https://docs.polymarket.com/trading/clients/builder

How it works:

  1. The operator (us) registers a builder code on Polymarket — a
     short identifier (e.g. ``pantheon``) tied to a payout address.
  2. Every CLOB order we submit carries that builder code as an
     extra field on the signed `OrderArgs`.
  3. When the order fills, Polymarket pays a configurable fraction of
     the taker fee to the builder's payout address, daily, in USDC.
  4. Maker rebates and builder fees are independent — a maker order
     can still earn a rebate AND have a builder code attached.

This module is a thin accounting + signing helper:

  * ``BuilderConfig`` — the operator's identity (code + payout).
  * ``BuilderLedger`` — append-only record of fills with builder
    attribution + estimated USDC accrued.
  * ``estimate_builder_fee_bps()`` — what we expect to earn per fill,
    given the category fee table and a configurable builder share.

The actual signing path lives in ``strategos.polymarket_clob`` —
``OrderRequest.builder_code`` is plumbed through ``OrderArgs`` so
py-clob-client-v2's signed order carries it. This module does not
touch the network; it accounts.

Why this matters for Pantheon:

  Every Boule deliberation produces a structured ``Thesis`` with a
  recommended trade. If a user executes that recommendation through
  our deployment, the builder code attribution turns the deliberation
  into a USDC revenue stream — no token, no subscription, no custody.
  This is the "actual answer to 'how does InsightAgent make money?'"
  called out in the Agora Agents Hackathon research notes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# Per-category builder share — the published V2 default is 20% of the
# taker fee (5% of total fee revenue net of maker rebates). Polymarket
# can dial this per program; operator overrides via env.
DEFAULT_BUILDER_SHARE = float(
    os.environ.get("POLYMARKET_BUILDER_SHARE", "0.20")
)

# Same V2 fee schedule used by execution_mode + maker_rebate. Kept
# duplicated rather than imported to keep this module dependency-free
# for builder-only analytics use cases (notebooks, audits).
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


@dataclass(frozen=True)
class BuilderConfig:
    """Operator-side configuration for the builder-code program.

    Attributes:
        code: the builder identifier registered on Polymarket. Short
              alphanumeric string; max 32 chars per the spec.
        payout_address: 0x-prefixed Polygon address that receives the
              daily USDC builder fees. Required.
        builder_share: the protocol-set fraction of the taker fee that
              flows to the builder. Default 0.20 (20%).
    """

    code: str
    payout_address: str
    builder_share: float = DEFAULT_BUILDER_SHARE

    def __post_init__(self) -> None:
        if not self.code or len(self.code) > 32:
            raise ValueError(f"builder code must be 1-32 chars, got: {self.code!r}")
        if not self.payout_address.startswith("0x") or len(self.payout_address) != 42:
            raise ValueError(
                f"payout_address must be a 0x-prefixed 20-byte hex; got {self.payout_address!r}"
            )
        if not 0.0 <= self.builder_share <= 1.0:
            raise ValueError(f"builder_share must be in [0, 1]; got {self.builder_share}")


@dataclass
class BuilderFill:
    """One row of builder-fee accounting per executed fill."""

    trade_id: str
    market_id: str
    category: str
    notional_usdc: float
    nominal_taker_fee_bps: float
    builder_share: float
    expected_builder_fee_usdc: float
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuilderLedger:
    """Append-only ledger of builder-attributed fills."""

    config: BuilderConfig
    rows: list[BuilderFill] = field(default_factory=list)

    def book(
        self,
        *,
        trade_id: str,
        market_id: str,
        category: str | None,
        notional_usdc: float,
        raw: dict[str, Any] | None = None,
    ) -> BuilderFill:
        """Record a fill that originated from our builder code."""
        cat_key = (category or "other").lower()
        nominal_bps = float(
            TAKER_FEE_BPS_BY_CATEGORY.get(cat_key, TAKER_FEE_BPS_BY_CATEGORY["other"])
        )
        notional = max(0.0, float(notional_usdc))
        expected = notional * nominal_bps * self.config.builder_share / 10_000.0
        row = BuilderFill(
            trade_id=trade_id,
            market_id=market_id,
            category=cat_key,
            notional_usdc=notional,
            nominal_taker_fee_bps=nominal_bps,
            builder_share=self.config.builder_share,
            expected_builder_fee_usdc=expected,
            raw=raw or {},
        )
        self.rows.append(row)
        return row

    def totals(self) -> dict[str, float]:
        """Aggregate builder revenue across the ledger."""
        total_notional = sum(r.notional_usdc for r in self.rows)
        total_revenue = sum(r.expected_builder_fee_usdc for r in self.rows)
        return {
            "fills": float(len(self.rows)),
            "total_notional_usdc": total_notional,
            "expected_builder_revenue_usdc": total_revenue,
            "effective_revenue_bps": (
                total_revenue / total_notional * 10_000.0
                if total_notional > 0
                else 0.0
            ),
            "payout_address": self.config.payout_address,
            "builder_code": self.config.code,
        }

    def by_category(self) -> dict[str, dict[str, float]]:
        """Per-category revenue breakdown for cohort analysis."""
        out: dict[str, dict[str, float]] = {}
        for r in self.rows:
            agg = out.setdefault(
                r.category,
                {"fills": 0.0, "notional_usdc": 0.0, "revenue_usdc": 0.0},
            )
            agg["fills"] += 1.0
            agg["notional_usdc"] += r.notional_usdc
            agg["revenue_usdc"] += r.expected_builder_fee_usdc
        return out


def estimate_builder_fee_bps(
    category: str,
    builder_share: float = DEFAULT_BUILDER_SHARE,
) -> float:
    """Back-of-envelope: builder fee in bps for a given category.

    Useful for sizing the *expected* revenue of a strategy without
    plumbing a real ledger. Geopolitics + world_events earn nothing
    (fee-free); crypto earns the most.
    """
    cat = TAKER_FEE_BPS_BY_CATEGORY.get(category.lower(), TAKER_FEE_BPS_BY_CATEGORY["other"])
    return cat * builder_share


def project_revenue(
    *,
    n_fills_per_day: float,
    avg_notional_usdc: float,
    category_mix: dict[str, float] | None = None,
    builder_share: float = DEFAULT_BUILDER_SHARE,
) -> dict[str, float]:
    """Project annual builder revenue at a given throughput.

    ``category_mix`` is a {category: weight} dict that sums to 1.0.
    If None, defaults to an even split across politics/sports/economics
    (a reasonable starting prior for a general-purpose council).
    """
    mix = category_mix or {"politics": 0.5, "sports": 0.3, "economics": 0.2}
    total_weight = sum(mix.values()) or 1.0
    weighted_bps = 0.0
    for cat, w in mix.items():
        cat_bps = TAKER_FEE_BPS_BY_CATEGORY.get(cat.lower(), TAKER_FEE_BPS_BY_CATEGORY["other"])
        weighted_bps += (w / total_weight) * cat_bps * builder_share

    daily_notional = n_fills_per_day * avg_notional_usdc
    annual_notional = daily_notional * 365.0
    annual_revenue = annual_notional * weighted_bps / 10_000.0

    return {
        "annual_notional_usdc": annual_notional,
        "weighted_builder_bps": weighted_bps,
        "annual_revenue_usdc": annual_revenue,
        "builder_share": builder_share,
    }


def build_default_config() -> BuilderConfig | None:
    """Construct a ``BuilderConfig`` from env vars if both are set.

    Reads ``POLYMARKET_BUILDER_CODE`` and ``POLYMARKET_BUILDER_PAYOUT``.
    Returns ``None`` if either is missing — caller falls back to a
    non-attributed order. The builder code is registered separately
    via the Polymarket-side admin flow; we do not write to chain here.
    """
    code = os.environ.get("POLYMARKET_BUILDER_CODE")
    payout = os.environ.get("POLYMARKET_BUILDER_PAYOUT")
    if not code or not payout:
        return None
    try:
        return BuilderConfig(code=code, payout_address=payout)
    except ValueError:
        return None
