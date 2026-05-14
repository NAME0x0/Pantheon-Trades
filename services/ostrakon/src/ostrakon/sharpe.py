from __future__ import annotations

import math


def sharpe_ratio(returns: list[float], risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio from a list of trade returns (as fractions)."""
    if len(returns) < 2:
        return 0.0
    n = len(returns)
    mean_r = sum(returns) / n
    excess = [r - risk_free for r in returns]
    variance = sum((r - mean_r) ** 2 for r in excess) / (n - 1)
    std = math.sqrt(variance) if variance > 0 else 1e-9
    # Annualize assuming ~250 trading opportunities per year
    return round((mean_r / std) * math.sqrt(250), 4)
