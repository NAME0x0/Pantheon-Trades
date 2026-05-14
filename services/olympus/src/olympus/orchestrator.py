"""Olympus orchestrator — top-level system state machine.

Listens for cross-service health signals and decides whether new trades may
proceed. Olympus does NOT execute trades itself — it gates them by toggling
``OlympusState`` between STANDBY / ACTIVE / DEGRADED / PAUSED / RECOVERY.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from olympus.state import OlympusState, SystemState


@dataclass
class ServiceHealth:
    name: str
    healthy: bool
    note: str = ""


@dataclass
class OlympusOrchestrator:
    state: OlympusState = field(default_factory=OlympusState)
    services: dict[str, ServiceHealth] = field(default_factory=dict)

    def report(self, health: ServiceHealth) -> None:
        self.services[health.name] = health
        self._reconcile()

    def _reconcile(self) -> None:
        # Critical services that must be healthy for ACTIVE.
        critical = {"pythia", "boule", "areopagus", "strategos"}
        critical_health = [self.services.get(n) for n in critical]
        critical_healthy = all(h is not None and h.healthy for h in critical_health)

        if not critical_healthy:
            if self.state.state in (SystemState.ACTIVE,):
                self.state.transition(SystemState.DEGRADED, reason="critical service unhealthy")
            elif self.state.state is SystemState.STANDBY:
                # cannot move into ACTIVE; stay
                return
        else:
            if self.state.state is SystemState.STANDBY:
                self.state.transition(SystemState.ACTIVE, reason="all critical services healthy")
            elif self.state.state is SystemState.DEGRADED:
                self.state.transition(SystemState.ACTIVE, reason="services recovered")

    def pause(self, reason: str) -> tuple[bool, str]:
        return self.state.transition(SystemState.PAUSED, reason=reason)

    def resume(self) -> tuple[bool, str]:
        return self.state.transition(SystemState.RECOVERY, reason="manual resume")

    @property
    def accepts_new_trades(self) -> bool:
        return self.state.accepts_new_trades
