from __future__ import annotations



def volatility_score(price_std_24h: float, price_mean: float, baseline_vol: float = 0.05) -> float:
    """Normalized 0-1 volatility regime score. Higher = more volatile."""
    if price_mean <= 0:
        return 0.0
    cv = price_std_24h / price_mean
    normalized = min(cv / baseline_vol, 2.0) / 2.0
    return round(normalized, 6)


def is_high_vol(score: float, threshold: float = 0.70) -> bool:
    return score >= threshold
