"""Recall helpers — surface memory entries inside agent prompts."""

from __future__ import annotations

from boule.memory.store import MemoryEntry


def format_for_prompt(entries: list[MemoryEntry]) -> str:
    if not entries:
        return "(no prior history on this market)"
    lines = []
    for entry in entries[-3:]:
        lines.append(
            f"- {entry.at.date()}: thesis {entry.thesis_id[:8]} "
            f"voted {entry.direction} p={entry.council_probability:.2f} "
            f"outcome={entry.outcome}"
        )
    return "\n".join(lines)
