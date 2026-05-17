"""Cross-venue basis-arbitrage feature.

When the same real-world question prices differently on Polymarket vs
Kalshi vs the sportsbook consensus, the gap is a *clean basis*. After
fees + slippage, anything left over is a tradable inefficiency.

This module is pure math — Pythia adapters (kalshi, odds_api,
manifold) supply the comparison venues. Apollo composes them into a
bounded probability bias on the council's oracle estimate.

Mechanics:

  * ``basis_spread(polymarket_p, venue_p) → float`` — signed delta
    in probability points.
  * ``bias_from_basis(spread, fees_bps, slippage_bps) → float`` —
    after subtracting expected costs, returns the bias direction +
    magnitude. Capped so a 50pp gap doesn't recommend a 50pp bet.
  * ``compose(...)`` — full feature struct including venue label,
    fee bucket, post-cost net basis, and final bias.

Why this is the highest-S/N entry in docs/EDGE_SOURCES.md: the
underlying mispricing is *empirical*, not predicted. The market
either agrees or it doesn't; the costs either survive or they don't.
No need to model the world — only the spread.
"""

from __future__ import annotations

from dataclasses import dataclass

# Capped bias contribution. Aligns with the other Apollo features —
# no single source can move oracle by more than 5 probability points.
MAX_BASIS_BIAS = 0.05

# Default fee allowance to subtract before declaring a tradable basis.
# Polymarket V2 round-trip taker is ~400 bps for politics, 720 bps for
# crypto. We use 500 bps mid as a conservative floor; the operator can
# pass a tighter bound for known-cheap categories.
DEFAULT_FEES_BPS = 500.0
DEFAULT_SLIPPAGE_BPS = 50.0


@dataclass(frozen=True)
class BasisArbFeature:
    """One cross-venue basis observation."""

    polymarket_p: float
    venue_p: float | None
    venue_label: str
    raw_spread: float | None
    cost_bps: float
    net_basis_pp: float | None
    bias: float
    tradable: bool


def basis_spread(polymarket_p: float, venue_p: float | None) -> float | None:
    """Signed delta: positive means the venue thinks YES is more
    likely than Polymarket.

    Returns None when either side lacks data.
    """
    if venue_p is None:
        return None
    return float(venue_p) - float(polymarket_p)


def bias_from_basis(
    spread: float | None,
    *,
    fees_bps: float = DEFAULT_FEES_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    max_bias: float = MAX_BASIS_BIAS,
) -> float:
    """Subtract cost-of-trade from the raw spread + cap the residual.

    Convention: positive spread → bias toward YES, capped at
    ``max_bias``. Negative spread → bias toward NO. A spread that
    doesn't cover round-trip costs returns 0.
    """
    if spread is None:
        return 0.0
    cost_pp = (fees_bps + slippage_bps) / 10_000.0
    # Subtract costs in absolute terms, preserving the sign.
    if abs(spread) <= cost_pp:
        return 0.0
    net = (abs(spread) - cost_pp) * (1.0 if spread > 0 else -1.0)
    # Map: a 20pp net residual → full max_bias. Saturating linear.
    scale = 0.20
    bias = max(-max_bias, min(max_bias, (net / scale) * max_bias))
    return bias


def compose(
    *,
    polymarket_p: float,
    venue_p: float | None,
    venue_label: str = "venue",
    fees_bps: float = DEFAULT_FEES_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> BasisArbFeature:
    """Build the feature dataclass.

    ``tradable`` is True when the cost-net basis is non-zero after
    accounting for fees + slippage. Apollo down-weights signals
    where ``tradable`` is False — no point sizing against a basis
    you can't capture.
    """
    spread = basis_spread(polymarket_p, venue_p)
    if spread is None:
        return BasisArbFeature(
            polymarket_p=polymarket_p,
            venue_p=None,
            venue_label=venue_label,
            raw_spread=None,
            cost_bps=fees_bps + slippage_bps,
            net_basis_pp=None,
            bias=0.0,
            tradable=False,
        )
    cost_pp = (fees_bps + slippage_bps) / 10_000.0
    net = abs(spread) - cost_pp
    bias = bias_from_basis(spread, fees_bps=fees_bps, slippage_bps=slippage_bps)
    return BasisArbFeature(
        polymarket_p=polymarket_p,
        venue_p=venue_p,
        venue_label=venue_label,
        raw_spread=spread,
        cost_bps=fees_bps + slippage_bps,
        net_basis_pp=net,
        bias=bias,
        tradable=net > 0,
    )
