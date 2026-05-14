"""Execution latency tracker — records signal-to-fill ms per trade."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LatencyTracker:
    capacity: int = 256
    samples_ms: deque[float] = field(default_factory=lambda: deque(maxlen=256))

    def record(self, elapsed_ms: float) -> None:
        if elapsed_ms < 0:
            return
        self.samples_ms.append(elapsed_ms)

    @property
    def count(self) -> int:
        return len(self.samples_ms)

    @property
    def mean_ms(self) -> float:
        return sum(self.samples_ms) / self.count if self.count else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.samples_ms:
            return 0.0
        ordered = sorted(self.samples_ms)
        idx = max(0, int(0.95 * (len(ordered) - 1)))
        return ordered[idx]


class StopWatch:
    def __init__(self, tracker: LatencyTracker) -> None:
        self._tracker = tracker
        self._start = 0.0

    def __enter__(self) -> "StopWatch":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (time.monotonic() - self._start) * 1000.0
        self._tracker.record(elapsed_ms)
