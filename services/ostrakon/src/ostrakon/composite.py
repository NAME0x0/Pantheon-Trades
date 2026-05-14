"""Composite score blending Brier, Sharpe, and calibration."""

from __future__ import annotations


WEIGHTS = {"brier": 0.5, "sharpe": 0.3, "calibration": 0.2}


def composite_score(brier: float, sharpe: float, calibration_error: float) -> float:
    """Single 0-1 score where higher is better.

    - Brier mapped via (1 - brier) since lower Brier = better.
    - Sharpe clamped to [-2, 2] then normalised into [0, 1].
    - Calibration mapped via (1 - calibration_error).
    """
    brier_term = max(0.0, 1.0 - min(brier, 1.0))
    sharpe_clamped = max(-2.0, min(2.0, sharpe))
    sharpe_term = (sharpe_clamped + 2.0) / 4.0
    cal_term = max(0.0, 1.0 - min(calibration_error, 1.0))
    score = (
        WEIGHTS["brier"] * brier_term
        + WEIGHTS["sharpe"] * sharpe_term
        + WEIGHTS["calibration"] * cal_term
    )
    return round(score, 6)
