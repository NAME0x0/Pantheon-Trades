"""Polymarket scanner — surface basic facts about a market payload."""

from __future__ import annotations


def scan_polymarket_market(market: dict) -> list[str]:
    obs: list[str] = []
    if not market.get("active", True):
        obs.append("market reports inactive")
    if market.get("closed"):
        obs.append("market already closed")
    spread = float(market.get("spread", 0.0) or 0.0)
    if spread >= 0.08:
        obs.append(f"wide reported spread {spread:.2%}")
    vol = float(market.get("volume24hr") or market.get("volume") or 0.0)
    if vol < 5_000:
        obs.append(f"low 24h volume ${vol:,.0f}")
    return obs
