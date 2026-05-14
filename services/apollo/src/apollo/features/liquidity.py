from __future__ import annotations

import math

VOLUME_BASELINE = 50_000.0
OI_BASELINE = 100_000.0
SPREAD_MAX = 0.10


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def liquidity_score(volume_24h: float, open_interest: float, spread: float) -> float:
    """Normalized 0-1 liquidity score per SIGNAL_SPEC.md formula."""
    vol_term = 0.4 * math.log(max(volume_24h, 1.0) / VOLUME_BASELINE)
    oi_term = 0.4 * math.log(max(open_interest, 1.0) / OI_BASELINE)
    spread_term = 0.2 * (1.0 - min(spread / SPREAD_MAX, 1.0))
    return round(_sigmoid(vol_term + oi_term + spread_term), 6)
