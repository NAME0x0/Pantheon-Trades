"""Agent promotion — track credibility upgrades over time."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromotionLog:
    history: list[tuple[str, float]] = field(default_factory=list)

    def log(self, agent: str, new_weight: float) -> None:
        self.history.append((agent, new_weight))


def promote_if_eligible(
    agent: str,
    current_weight: float,
    rolling_brier: float,
    *,
    max_weight: float = 2.0,
    brier_ceiling: float = 0.18,
) -> float:
    """Increase agent weight when sustained Brier is excellent."""
    if rolling_brier > brier_ceiling:
        return current_weight
    bumped = min(max_weight, round(current_weight * 1.10, 4))
    return bumped
