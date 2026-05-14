"""Eyes — Argos's many-eyed price sampler.

Wraps several uncoordinated price oracles behind a single async surface.
Each ``Eye`` knows how to fetch a YES-side price for a given market_id. The
``Eyes`` aggregator returns the median across all reporting eyes, with
outliers (> 5pp from median) discarded.
"""

from __future__ import annotations

import asyncio
import statistics
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


OUTLIER_THRESHOLD = 0.05

Fetcher = Callable[[str], Awaitable[float | None]]


@dataclass(frozen=True)
class Eye:
    name: str
    fetch: Fetcher


class Eyes:
    def __init__(self, eyes: list[Eye]) -> None:
        if not eyes:
            raise ValueError("at least one Eye is required")
        self._eyes = eyes

    async def yes_price(self, market_id: str) -> float | None:
        results = await asyncio.gather(
            *[eye.fetch(market_id) for eye in self._eyes], return_exceptions=True
        )
        prices = [r for r in results if isinstance(r, float) and 0.0 <= r <= 1.0]
        if not prices:
            return None
        med = statistics.median(prices)
        inliers = [p for p in prices if abs(p - med) <= OUTLIER_THRESHOLD]
        if not inliers:
            return med
        return sum(inliers) / len(inliers)
