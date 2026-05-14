"""Liquidity monitor — emit observations on book depth + volume."""

from __future__ import annotations


def check_liquidity(volume_24h: float, open_interest: float) -> str | None:
    if volume_24h < 5_000:
        return f"thin volume_24h ${volume_24h:,.0f}"
    if open_interest < 10_000:
        return f"thin open_interest ${open_interest:,.0f}"
    return None
