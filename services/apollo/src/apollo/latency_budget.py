"""Per-tick latency budget so a scan never blows the cadence.

The runner targets a 30-second scan cadence; if scoring a single market
takes long enough that we cannot finish the queue, we drop later
candidates rather than fall behind. ``LatencyBudget.charge()`` is a
context manager that records the elapsed time and decrements the
remaining budget.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class LatencyBudget:
    total_seconds: float = 25.0
    elapsed_seconds: float = 0.0

    def exhausted(self) -> bool:
        return self.elapsed_seconds >= self.total_seconds

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.elapsed_seconds)

    @contextmanager
    def charge(self):
        start = time.monotonic()
        try:
            yield
        finally:
            self.elapsed_seconds += time.monotonic() - start

    def reset(self) -> None:
        self.elapsed_seconds = 0.0
