"""A canonical memo for one resolved market — the unit of RAG retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResolvedExample:
    market_id: str
    question: str
    category: str
    resolved_at: datetime
    final_yes_price: float
    outcome: int  # 1 if YES resolved, 0 if NO
    days_to_resolution_at_listing: float | None = None
    notes: str = ""

    def as_prose(self) -> str:
        """Pack into a single string suitable for an LLM context window."""
        outcome_label = "YES" if self.outcome == 1 else "NO"
        days = (
            f"{self.days_to_resolution_at_listing:.0f}d from listing"
            if self.days_to_resolution_at_listing is not None
            else "unknown horizon"
        )
        notes = f"\nNotes: {self.notes}" if self.notes else ""
        return (
            f"[{self.category}] {self.question}\n"
            f"  resolved {outcome_label} at "
            f"{self.resolved_at.date().isoformat()} "
            f"(final YES={self.final_yes_price:.3f}, {days}).{notes}"
        )
