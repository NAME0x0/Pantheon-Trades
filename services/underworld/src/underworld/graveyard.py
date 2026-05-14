"""Strategy graveyard — terminated strategies and why they died."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass(frozen=True)
class GraveEntry:
    strategy_id: str
    name: str
    cause_of_death: str
    final_brier: float
    final_drawdown: float
    at: datetime = field(default_factory=utc_now)


@dataclass
class Graveyard:
    entries: list[GraveEntry] = field(default_factory=list)

    def bury(
        self,
        strategy_id: str,
        name: str,
        cause_of_death: str,
        *,
        final_brier: float,
        final_drawdown: float,
    ) -> GraveEntry:
        entry = GraveEntry(
            strategy_id=strategy_id,
            name=name,
            cause_of_death=cause_of_death,
            final_brier=final_brier,
            final_drawdown=final_drawdown,
        )
        self.entries.append(entry)
        return entry

    def lookup(self, strategy_id: str) -> GraveEntry | None:
        for entry in self.entries:
            if entry.strategy_id == strategy_id:
                return entry
        return None

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for entry in self.entries:
            out[entry.cause_of_death] = out.get(entry.cause_of_death, 0) + 1
        return out
