"""Perpetual-futures funding + OI signal for crypto markets.

For Polymarket / Kalshi binaries that resolve on a crypto price level
("Will BTC be above $X by Y?"), positioning on the perps book is a
leading indicator. Extreme positive funding (longs paying shorts
heavily) historically precedes liquidation cascades; extreme OI
expansion alongside that funding compounds the risk.

This module is pure math — Pythia's ``BinancePerpsSource`` supplies
the raw numbers; we turn them into a unit-less directional bias.

Two inputs combined:

  * ``funding_z`` — z-score of latest funding vs rolling window.
  * ``oi_delta_pct`` — percent change in OI over the same window.

Output:

  * ``directional_bias`` — signed delta in probability space.
    Extreme positive funding (>+2σ) → bearish on the spot direction
    → negative bias for a "price-up" YES market.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_PERPS_BIAS = 0.05  # match the other Apollo feature caps

# When |funding_z| crosses this, we start applying bias. Below this,
# perps positioning is neutral and we contribute zero.
FUNDING_Z_THRESHOLD = 1.0


@dataclass(frozen=True)
class PerpsSignalFeature:
    symbol: str
    funding_z: float | None
    oi_delta_pct: float | None
    directional_bias: float        # signed probability bias for YES
    cascade_risk_score: float      # [0, 1] composite "blow-up risk"


def cascade_risk(funding_z: float | None, oi_delta_pct: float | None) -> float:
    """Composite [0, 1] score: how at-risk is the perps book?

    High positive funding + high OI growth → near 1.0.
    Neutral funding + flat OI → near 0.0.
    Negative funding + flat OI → near 0.0 (shorts pay longs, less
    blow-up risk on the spot-up side).
    """
    if funding_z is None:
        f_part = 0.5
    else:
        # Tanh of funding_z scaled to put 2σ near saturation.
        f_part = (math.tanh(funding_z / 2.0) + 1.0) / 2.0
    if oi_delta_pct is None:
        oi_part = 0.5
    else:
        # 20% OI growth → ~0.86; -20% → ~0.14.
        oi_part = (math.tanh(oi_delta_pct * 5.0) + 1.0) / 2.0
    return round(0.6 * f_part + 0.4 * oi_part, 4)


def compose(
    *,
    symbol: str,
    funding_z: float | None,
    oi_delta_pct: float | None = None,
    direction_convention: str = "yes_means_up",
) -> PerpsSignalFeature:
    """Build the feature dataclass.

    ``direction_convention``: "yes_means_up" (default) for markets
    phrased as "Will price be above X". Flip if your market is the
    inverse.
    """
    risk = cascade_risk(funding_z, oi_delta_pct)
    # Bias only if funding is meaningfully extreme.
    bias = 0.0
    if funding_z is not None and abs(funding_z) >= FUNDING_Z_THRESHOLD:
        # Saturating sigmoid: 2σ funding → ~half of MAX_PERPS_BIAS,
        # 4σ → ~full MAX_PERPS_BIAS. Sign convention: positive funding
        # (longs over-leveraged) → bearish on UP direction → negative
        # bias for "yes_means_up" markets.
        magnitude = math.tanh((abs(funding_z) - FUNDING_Z_THRESHOLD) / 2.0) * MAX_PERPS_BIAS
        sign = -1.0 if funding_z > 0 else 1.0  # contrarian on extreme funding
        if direction_convention != "yes_means_up":
            sign = -sign
        bias = sign * magnitude
    return PerpsSignalFeature(
        symbol=symbol,
        funding_z=funding_z,
        oi_delta_pct=oi_delta_pct,
        directional_bias=round(bias, 6),
        cascade_risk_score=risk,
    )
