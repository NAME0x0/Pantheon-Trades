"""Hallucination log — agent claims that did not match reality."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass(frozen=True)
class Hallucination:
    thesis_id: str
    agent: str
    claim: str
    rebuttal: str
    at: datetime = field(default_factory=utc_now)


@dataclass
class HallucinationLog:
    entries: list[Hallucination] = field(default_factory=list)

    def record(
        self, thesis_id: str, agent: str, claim: str, rebuttal: str
    ) -> Hallucination:
        entry = Hallucination(
            thesis_id=thesis_id, agent=agent, claim=claim, rebuttal=rebuttal
        )
        self.entries.append(entry)
        return entry

    def by_agent(self, agent: str) -> list[Hallucination]:
        return [e for e in self.entries if e.agent == agent]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            out[e.agent] = out.get(e.agent, 0) + 1
        return out
