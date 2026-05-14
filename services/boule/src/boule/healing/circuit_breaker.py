"""Circuit breaker — short-circuits flaky downstreams (Claude API, Redis)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_timeout_seconds: float = 30.0
    failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    opened_at: float = 0.0

    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()

    def allow(self) -> bool:
        if self.state is CircuitState.CLOSED:
            return True
        if self.state is CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.reset_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: allow a probe
