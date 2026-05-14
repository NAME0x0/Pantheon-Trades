"""Market scanner — cheap heuristics applied to a Signal before deliberation."""

from __future__ import annotations

from pantheon_core.schema import Signal


def quick_observations(signal: Signal) -> list[str]:
    obs: list[str] = []
    if signal.edge_abs > 0.20:
        obs.append(f"large edge {signal.edge_abs:.2%} — verify oracle inputs")
    if signal.spread > 0.06:
        obs.append(f"wide spread {signal.spread:.2%}")
    if signal.staleness_seconds > 200:
        obs.append(f"data {signal.staleness_seconds}s stale")
    if signal.liquidity_score < 0.55:
        obs.append(f"thin liquidity score {signal.liquidity_score:.2f}")
    if signal.days_to_resolution is not None and signal.days_to_resolution < 3:
        obs.append("resolution within 3 days — gamma risk elevated")
    return obs
