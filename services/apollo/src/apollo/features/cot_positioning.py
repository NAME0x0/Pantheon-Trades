"""CFTC Commitments of Traders positioning signal.

For Polymarket / Kalshi markets resolved on a CFTC-tracked futures
underlying (S&P 500 above X, gold above Y, oil above Z), the
speculator positioning z-score is a documented mean-reversion
signal. Extreme positive z (crowded longs) tends to precede
short-term tops; extreme negative tends to precede bottoms.

Bounded contribution: ±0.05 like the rest of the new feature suite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_COT_BIAS = 0.05

# Below |z| = 1, no contribution. This is a tail signal.
COT_Z_THRESHOLD = 1.0


@dataclass(frozen=True)
class CotPositioningFeature:
    market_code: str
    speculator_z: float | None
    directional_bias: float


def compose(
    *,
    market_code: str,
    speculator_z: float | None,
    direction_convention: str = "yes_means_up",
) -> CotPositioningFeature:
    """Build the feature dataclass.

    Contrarian convention: crowded-long speculators (positive z) →
    bearish on UP direction → negative bias on a "yes_means_up"
    market. Inverse for crowded shorts.
    """
    if speculator_z is None or abs(speculator_z) < COT_Z_THRESHOLD:
        return CotPositioningFeature(
            market_code=market_code,
            speculator_z=speculator_z,
            directional_bias=0.0,
        )
    magnitude = math.tanh((abs(speculator_z) - COT_Z_THRESHOLD) / 2.0) * MAX_COT_BIAS
    sign = -1.0 if speculator_z > 0 else 1.0
    if direction_convention != "yes_means_up":
        sign = -sign
    return CotPositioningFeature(
        market_code=market_code,
        speculator_z=speculator_z,
        directional_bias=round(sign * magnitude, 6),
    )
