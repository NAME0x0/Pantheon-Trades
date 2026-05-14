"""Position adjustments — partial exits and re-sizing prior to full exit.

These helpers compute *new* sizes/stops without mutating the original
``Position``. The monitor decides how to act on the result.
"""

from __future__ import annotations

from dataclasses import dataclass

from argos.pnl import Position


@dataclass(frozen=True)
class SizeAdjustment:
    new_size_usdc: float
    note: str


def trim_to_half(position: Position) -> SizeAdjustment:
    """Reduce size to half once profit > 50% of target distance."""
    return SizeAdjustment(
        new_size_usdc=position.size_usdc * 0.5,
        note="trimmed to half on partial target",
    )


def tighten_stop(position: Position) -> float:
    """Lift stop to break-even once we cross half-way to target."""
    half_way = position.entry_price + 0.5 * (position.target - position.entry_price)
    if position.current_price >= half_way:
        return max(position.stop, position.entry_price)
    return position.stop
