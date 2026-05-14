"""Spread scanner — flag illiquid books by bid/ask spread."""

from __future__ import annotations


def detect_wide_spread(bid: float, ask: float, soft: float = 0.08, hard: float = 0.12) -> str | None:
    spread = max(0.0, ask - bid)
    if spread >= hard:
        return f"hard-wide spread {spread:.2%}"
    if spread >= soft:
        return f"wide spread {spread:.2%}"
    return None
