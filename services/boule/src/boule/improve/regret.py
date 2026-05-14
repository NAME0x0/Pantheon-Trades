"""Regret accounting — quantify expected vs realised PnL per thesis."""

from __future__ import annotations


def realised_regret(expected_pnl: float, realised_pnl: float) -> float:
    """Positive regret = we did worse than expected."""
    return round(expected_pnl - realised_pnl, 6)


def aggregate_regret(records: list[tuple[float, float]]) -> dict[str, float]:
    if not records:
        return {"count": 0.0, "mean_regret": 0.0, "max_regret": 0.0}
    regrets = [realised_regret(e, r) for e, r in records]
    return {
        "count": float(len(regrets)),
        "mean_regret": round(sum(regrets) / len(regrets), 6),
        "max_regret": round(max(regrets), 6),
    }
