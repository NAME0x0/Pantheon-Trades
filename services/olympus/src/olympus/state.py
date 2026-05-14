from __future__ import annotations

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

from pantheon_core.schema import utc_now


class SystemState(str, Enum):
    STANDBY = "standby"
    ACTIVE = "active"
    DEGRADED = "degraded"
    PAUSED = "paused"
    RECOVERY = "recovery"


VALID_TRANSITIONS: dict[SystemState, set[SystemState]] = {
    SystemState.STANDBY: {SystemState.ACTIVE},
    SystemState.ACTIVE: {SystemState.DEGRADED, SystemState.PAUSED},
    SystemState.DEGRADED: {SystemState.ACTIVE, SystemState.PAUSED},
    SystemState.PAUSED: {SystemState.RECOVERY, SystemState.STANDBY},
    SystemState.RECOVERY: {SystemState.ACTIVE, SystemState.STANDBY},
}


@dataclass
class OlympusState:
    state: SystemState = SystemState.STANDBY
    paused_at: datetime | None = None
    pause_reason: str | None = None
    transitions: list[tuple[str, str, datetime]] = field(default_factory=list)

    def transition(self, target: SystemState, reason: str = "") -> tuple[bool, str]:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            return False, f"Cannot go from {self.state} to {target}"
        old = self.state
        self.state = target
        now = utc_now()
        self.transitions.append((old.value, target.value, now))
        if target == SystemState.PAUSED:
            self.paused_at = now
            self.pause_reason = reason
        elif old == SystemState.PAUSED:
            self.paused_at = None
            self.pause_reason = None
        return True, f"{old.value} -> {target.value}"

    @property
    def is_active(self) -> bool:
        return self.state == SystemState.ACTIVE

    @property
    def accepts_new_trades(self) -> bool:
        return self.state in (SystemState.ACTIVE,)
