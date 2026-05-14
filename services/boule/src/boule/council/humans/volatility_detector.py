"""Volatility regime detector — label the current vol bucket."""

from __future__ import annotations


def detect_volatility_regime(std_24h: float, price_mean: float) -> str:
    if price_mean <= 0:
        return "unknown"
    cv = std_24h / price_mean
    if cv >= 0.20:
        return "extreme"
    if cv >= 0.10:
        return "high"
    if cv >= 0.05:
        return "moderate"
    return "low"
