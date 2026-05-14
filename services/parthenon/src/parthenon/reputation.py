"""Reputation summary derived from archived outcomes.

The agent leaderboard is rebuilt by scanning archived ``outcome`` entries
across all manifests and aggregating per-agent accuracy. This module
returns the aggregation without touching IPFS — the caller wires in the
streaming source.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class AgentReputation:
    agent: str
    predictions: int = 0
    correct: int = 0
    brier_sum: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.predictions if self.predictions else 0.0

    @property
    def brier(self) -> float:
        return self.brier_sum / self.predictions if self.predictions else 1.0


def aggregate(outcomes: list[dict]) -> list[AgentReputation]:
    """``outcomes`` is a list of post-mortem dicts with ``agent_accuracy`` and ``agent_probabilities``."""
    by_agent: dict[str, AgentReputation] = defaultdict(lambda: AgentReputation(agent=""))
    for outcome in outcomes:
        actual = int(outcome.get("actual_outcome", 0))
        accuracies: dict = outcome.get("agent_accuracy", {})
        probabilities: dict = outcome.get("agent_probabilities", {})
        for agent, was_right in accuracies.items():
            rep = by_agent[agent]
            rep.agent = agent
            rep.predictions += 1
            if was_right:
                rep.correct += 1
            prob = float(probabilities.get(agent, 0.5))
            rep.brier_sum += (prob - actual) ** 2
    return sorted(by_agent.values(), key=lambda r: r.brier)
