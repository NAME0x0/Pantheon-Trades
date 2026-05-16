"""Drawdown-aware Kelly multiplier.

Half-Kelly is constitutional, but a system that just lost 30% of book
equity should not keep sizing the next trade as if nothing happened.
This module derives a multiplier in ``[floor, 1.0]`` from the current
drawdown that callers fold into the final position size:

    final_pct = half_kelly * drawdown_multiplier(current, peak)

The shape is a clamped linear ramp:

    dd <= 0          -> 1.0  (at or above peak — no penalty)
    0 < dd < cap     -> linear interpolation between 1.0 and ``floor``
    dd >= cap        -> ``floor``  (deepest penalty, never zero)

Defaults: ``floor=0.2``, ``cap=0.30``. So a 15% DD downshifts to
~0.6× sizing; a 30% DD floors at 0.2×. A non-zero floor matters:
zeroing out sizing during DD freezes the system into the very state
it needs to trade out of.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_FLOOR = 0.2
DEFAULT_CAP_DRAWDOWN = 0.30


@dataclass(frozen=True)
class DrawdownState:
    current_equity: float
    peak_equity: float

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        if self.current_equity >= self.peak_equity:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity


def drawdown_multiplier(
    current_equity: float,
    peak_equity: float,
    floor: float = DEFAULT_FLOOR,
    cap: float = DEFAULT_CAP_DRAWDOWN,
) -> float:
    """Return Kelly scaler in ``[floor, 1.0]`` based on drawdown depth."""
    if peak_equity <= 0 or current_equity >= peak_equity:
        return 1.0
    if cap <= 0:
        return 1.0
    dd = (peak_equity - current_equity) / peak_equity
    if dd >= cap:
        return floor
    # Linear ramp: dd=0 -> 1.0, dd=cap -> floor.
    return 1.0 - (1.0 - floor) * (dd / cap)


def apply_drawdown(
    size_pct: float,
    current_equity: float,
    peak_equity: float,
    floor: float = DEFAULT_FLOOR,
    cap: float = DEFAULT_CAP_DRAWDOWN,
) -> tuple[float, float]:
    """Return ``(adjusted_size, multiplier)``."""
    mult = drawdown_multiplier(current_equity, peak_equity, floor=floor, cap=cap)
    return size_pct * mult, mult
