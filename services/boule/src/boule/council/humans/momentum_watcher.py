"""Momentum watcher — flag fast directional moves over the last N samples."""

from __future__ import annotations


JUMP_THRESHOLD = 0.05


def detect_momentum(price_history: list[float]) -> str | None:
    if len(price_history) < 3:
        return None
    head = price_history[0]
    tail = price_history[-1]
    delta = tail - head
    if abs(delta) >= JUMP_THRESHOLD:
        direction = "bullish" if delta > 0 else "bearish"
        return f"{direction} momentum {head:.3f} -> {tail:.3f}"
    return None
