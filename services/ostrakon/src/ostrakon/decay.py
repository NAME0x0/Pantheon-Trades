"""Time-decayed weighting — older predictions count for less."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from pantheon_core.schema import utc_now


HALF_LIFE_DAYS = 30.0


def decay_weight(prediction_time: datetime, half_life_days: float = HALF_LIFE_DAYS) -> float:
    age = (utc_now() - prediction_time).total_seconds() / 86_400
    if age <= 0:
        return 1.0
    return math.exp(-math.log(2) * age / half_life_days)


def decayed_brier(
    timed_predictions: list[tuple[datetime, float, int]],
    half_life_days: float = HALF_LIFE_DAYS,
) -> float:
    if not timed_predictions:
        return 0.0
    num = 0.0
    den = 0.0
    for ts, prob, outcome in timed_predictions:
        w = decay_weight(ts, half_life_days)
        num += w * (prob - outcome) ** 2
        den += w
    return round(num / den, 6) if den > 0 else 0.0
