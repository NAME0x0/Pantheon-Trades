"""Lessons learned — promote repeated broken-assumption patterns into rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now


PROMOTION_THRESHOLD = 3


@dataclass(frozen=True)
class Lesson:
    pattern: str
    occurrences: int
    suggested_rule: str
    at: datetime = field(default_factory=utc_now)


def derive_lessons(broken_assumptions: list[str]) -> list[Lesson]:
    """Promote any assumption seen >= PROMOTION_THRESHOLD times into a Lesson."""
    counts = Counter(broken_assumptions)
    return [
        Lesson(
            pattern=pattern,
            occurrences=count,
            suggested_rule=_rule_for(pattern),
        )
        for pattern, count in counts.items()
        if count >= PROMOTION_THRESHOLD
    ]


def _rule_for(pattern: str) -> str:
    table = {
        "overconfident_probability_estimate": (
            "Cap individual agent confidence at 0.85 unless quorum agrees"
        ),
        "large_probability_error": (
            "Add calibration discount when oracle deviates from market by > 20pp"
        ),
        "stale_data": "Tighten MAX_STALENESS to 180s for this category",
    }
    return table.get(pattern, "Operator review required")
