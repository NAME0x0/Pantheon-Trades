"""Lightweight resolution simulator — deterministic oracle for backtests.

Provides ``binomial_resolver`` that uses the council's own probability as
the Bernoulli parameter, and ``historic_resolver`` that looks up a
market_id in a supplied dict of known resolutions.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime
from typing import Mapping


def historic_resolver(known: Mapping[str, float]) -> Callable[[str, datetime | None], float]:
    def resolve(market_id: str, _resolution_date: datetime | None) -> float:
        return float(known.get(market_id, 0.5))
    return resolve


def binomial_resolver(seed: int = 0) -> Callable[[str, datetime | None], float]:
    rng = random.Random(seed)

    def resolve(_market_id: str, _resolution_date: datetime | None) -> float:
        return 1.0 if rng.random() < 0.5 else 0.0

    return resolve


def biased_resolver(market_probability: float, seed: int = 0) -> Callable[[str, datetime | None], float]:
    rng = random.Random(seed)

    def resolve(_market_id: str, _resolution_date: datetime | None) -> float:
        return 1.0 if rng.random() < market_probability else 0.0

    return resolve
