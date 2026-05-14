"""Reward schedule — multiplicative weight bumps for strong calls."""

from __future__ import annotations


REWARD_CALIBRATED_WIN = 1.05
REWARD_HIGH_CONVICTION_WIN = 1.10
REWARD_DETECTED_TAIL_RISK = 1.07


def apply_reward(current_weight: float, kind: str, *, ceiling: float = 2.0) -> float:
    factor = {
        "calibrated_win": REWARD_CALIBRATED_WIN,
        "high_conviction_win": REWARD_HIGH_CONVICTION_WIN,
        "detected_tail_risk": REWARD_DETECTED_TAIL_RISK,
    }.get(kind, 1.0)
    return min(ceiling, round(current_weight * factor, 4))
