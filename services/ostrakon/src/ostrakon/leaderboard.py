"""Agent leaderboard — rank agents by credibility weight + Brier."""

from __future__ import annotations

from dataclasses import dataclass

from ostrakon.metrics import AgentMetrics


@dataclass(frozen=True)
class LeaderboardEntry:
    agent: str
    credibility_weight: float
    brier: float
    sharpe: float
    predictions: int
    rank: int


def build_leaderboard(metrics: list[AgentMetrics]) -> list[LeaderboardEntry]:
    """Sort agents by descending credibility weight, breaking ties on Brier."""
    sorted_metrics = sorted(
        metrics,
        key=lambda m: (-m.credibility_weight(), m.brier),
    )
    return [
        LeaderboardEntry(
            agent=m.agent,
            credibility_weight=m.credibility_weight(),
            brier=round(m.brier, 4),
            sharpe=round(m.sharpe, 4),
            predictions=m.prediction_count,
            rank=i + 1,
        )
        for i, m in enumerate(sorted_metrics)
    ]


def top_n(metrics: list[AgentMetrics], n: int = 5) -> list[LeaderboardEntry]:
    return build_leaderboard(metrics)[:n]
