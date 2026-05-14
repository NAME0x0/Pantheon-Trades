"""Token-bucket rate limiter shared across Pythia data sources.

CoinGecko, DeFiLlama and the news feeds all enforce per-IP rate limits that
will silently 429 us if we burst. Each adapter wraps its calls in a bucket
keyed by source name. Buckets are async-safe.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    rate_per_second: float
    capacity: float
    _tokens: float = 0.0
    _last_refill: float = 0.0
    _lock: asyncio.Lock | None = None

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, cost: float = 1.0) -> None:
        assert self._lock is not None
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_second)
                self._last_refill = now
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                shortfall = cost - self._tokens
                await asyncio.sleep(shortfall / self.rate_per_second)


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def register(self, name: str, rate_per_second: float, capacity: float) -> None:
        self._buckets[name] = TokenBucket(rate_per_second=rate_per_second, capacity=capacity)

    async def take(self, name: str, cost: float = 1.0) -> None:
        bucket = self._buckets.get(name)
        if bucket is None:
            return
        await bucket.acquire(cost)
