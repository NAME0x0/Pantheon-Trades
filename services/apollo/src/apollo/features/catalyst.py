"""Catalyst feature — how strongly upcoming events should move this market.

We take a list of upcoming events with their hours-to-event and a per-event
relevance weight in [0, 1]. Events closer in time and more relevant
contribute more. The score is sigmoid-squashed into [0, 1] so it composes
with the rest of the band scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalystEvent:
    """A scheduled event with potential to move the market.

    ``hours_until``: lead-time in hours. Negative values are treated as zero
    (the event is already underway). ``relevance``: how strongly we believe
    the event correlates with the market outcome in [0, 1].
    """

    description: str
    hours_until: float
    relevance: float


HALF_LIFE_HOURS = 72.0  # events farther out decay exponentially


def _decay(hours_until: float) -> float:
    h = max(hours_until, 0.0)
    return math.exp(-math.log(2) * h / HALF_LIFE_HOURS)


def catalyst_score(events: list[CatalystEvent] | None = None) -> float:
    """Aggregate catalyst pressure into a 0-1 score."""
    if not events:
        return 0.5  # neutral baseline when we have no catalyst data
    weighted = 0.0
    for ev in events:
        weighted += max(0.0, min(1.0, ev.relevance)) * _decay(ev.hours_until)
    # Squash with a sigmoid centred on weighted=1.0 so a single highly
    # relevant near-term event lands around 0.73.
    score = 1.0 / (1.0 + math.exp(-(weighted - 1.0)))
    return round(score, 6)
