"""Technical analyst — basic momentum + volatility narrative from price series."""

from __future__ import annotations

import math


def technical_summary(prices: list[float]) -> str:
    if len(prices) < 3:
        return "insufficient price history"
    head = prices[0]
    tail = prices[-1]
    mean = sum(prices) / len(prices)
    var = sum((p - mean) ** 2 for p in prices) / max(len(prices) - 1, 1)
    std = math.sqrt(var)
    cv = std / mean if mean > 0 else 0.0
    direction = "up" if tail > head else "down" if tail < head else "flat"
    return (
        f"{direction} trend {head:.3f} -> {tail:.3f} "
        f"(mean {mean:.3f}, cv {cv:.2%})"
    )
