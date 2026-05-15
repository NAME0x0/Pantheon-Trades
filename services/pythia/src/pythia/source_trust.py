"""Per-source trust scores used to weight contributions in fused features.

Trust is a multiplicative weight in (0, 1] that decays with consecutive
fetch failures and rebuilds on success. Sources that disagree with the
consensus are penalised slightly to discourage echo chambers.
"""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TRUST = 1.0
FAILURE_DECAY = 0.85
SUCCESS_RECOVERY = 1.10
MIN_TRUST = 0.10
MAX_TRUST = 1.0


@dataclass
class SourceTrust:
    name: str
    trust: float = DEFAULT_TRUST
    consecutive_failures: int = 0
    total_calls: int = 0
    failed_calls: int = 0

    def record_success(self) -> None:
        self.total_calls += 1
        self.consecutive_failures = 0
        self.trust = min(MAX_TRUST, self.trust * SUCCESS_RECOVERY)

    def record_failure(self) -> None:
        self.total_calls += 1
        self.failed_calls += 1
        self.consecutive_failures += 1
        self.trust = max(MIN_TRUST, self.trust * FAILURE_DECAY)


class TrustRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceTrust] = {}

    def ensure(self, name: str) -> SourceTrust:
        if name not in self._sources:
            self._sources[name] = SourceTrust(name=name)
        return self._sources[name]

    def trust(self, name: str) -> float:
        return self.ensure(name).trust

    def record(self, name: str, ok: bool) -> None:
        rec = self.ensure(name)
        rec.record_success() if ok else rec.record_failure()

    def snapshot(self) -> dict[str, float]:
        return {name: rec.trust for name, rec in self._sources.items()}
