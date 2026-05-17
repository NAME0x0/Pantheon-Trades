"""Macro-release basis feature from FRED series.

For prediction markets that resolve on a specific macro print (Fed
Funds, CPI, NFP, GDP, breakeven inflation), the binary question is
usually "will X be above Y?". We can compute a *basis signal* by
comparing the latest FRED release (or its YoY change) to the market's
threshold. The signal is the gap.

This module is pure math — Pythia's ``FredSource`` supplies the raw
FRED numbers; we turn the gap into a directional probability bias.

The mapping from `gap → probability bias` is deliberately conservative:
we cap the bias at ±0.30. Wider gaps don't mean more conviction —
they usually mean the binary is mis-targeted by the operator and the
trade is hot air.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_BIAS = 0.30  # cap the probability bias the macro feature can introduce


@dataclass(frozen=True)
class MacroBasisFeature:
    series_id: str
    latest_value: float | None
    threshold: float
    gap: float | None         # signed (latest - threshold)
    gap_normalised: float | None  # gap / threshold_scale
    yes_bias: float | None    # probability bias in [-MAX_BIAS, +MAX_BIAS]


def normalise_gap(gap: float, scale: float) -> float:
    """Squash a gap by tanh(gap / scale). Output in (-1, 1).

    ``scale`` should be the operator's expected band width — e.g. for
    Fed Funds at 25 bps moves, scale ≈ 0.25.
    """
    if scale <= 0:
        return 0.0
    return math.tanh(gap / scale)


def compose(
    *,
    series_id: str,
    latest_value: float | None,
    threshold: float,
    scale: float,
) -> MacroBasisFeature:
    """Build the feature from a latest FRED value vs an operator
    threshold.

    Returns no-bias defaults if ``latest_value`` is None (missing data).
    """
    if latest_value is None:
        return MacroBasisFeature(
            series_id=series_id,
            latest_value=None,
            threshold=threshold,
            gap=None,
            gap_normalised=None,
            yes_bias=None,
        )
    gap = latest_value - threshold
    norm = normalise_gap(gap, scale)
    yes_bias = max(-MAX_BIAS, min(MAX_BIAS, norm * MAX_BIAS))
    return MacroBasisFeature(
        series_id=series_id,
        latest_value=latest_value,
        threshold=threshold,
        gap=gap,
        gap_normalised=norm,
        yes_bias=yes_bias,
    )
