"""Underworld post-mortem — what actually happened, and what we got wrong.

A post-mortem captures four things per resolved trade:

  1. ``outcome`` — win/loss/push from PnL.
  2. ``broken_assumptions`` — any quantitative claim from the thesis that
     reality disproved (e.g. wildly mis-estimated probability).
  3. ``agent_accuracy`` — per-agent boolean: did each agent pick the right
     side of the market? An agent that predicted YES with p > 0.5 is
     accurate iff YES resolved.
  4. ``primary_failure`` — terse cause tag used by Olympus to drive
     credibility/exile decisions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pantheon_core.schema import utc_now


@dataclass
class PostMortem:
    pm_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str = ""
    market_id: str = ""
    direction: str = ""
    outcome: Literal["win", "loss", "push"] = "loss"
    actual_outcome: int = 0  # 1 if YES resolved, 0 if NO resolved
    entry_probability: float = 0.0
    resolution_probability: float = 0.0
    pnl_pct: float = 0.0
    primary_failure: str = ""
    broken_assumptions: list[str] = field(default_factory=list)
    hallucinations: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    agent_accuracy: dict[str, bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


def _classify_outcome(pnl_pct: float) -> Literal["win", "loss", "push"]:
    if pnl_pct > 0.001:
        return "win"
    if pnl_pct < -0.001:
        return "loss"
    return "push"


def _derive_actual_outcome(direction: str, outcome: str) -> int:
    """Reconstruct the market's actual resolution from our trade direction + result."""
    if outcome == "push":
        return -1  # ambiguous — push out of accuracy scoring
    won = outcome == "win"
    if direction == "YES":
        return 1 if won else 0
    return 0 if won else 1


def _agent_is_accurate(probability: float, actual_outcome: int) -> bool:
    """An agent is accurate iff its predicted probability is on the right side of 0.5."""
    if actual_outcome == -1:
        return False
    return (probability > 0.5) == (actual_outcome == 1)


class PostMortemRunner:
    def __init__(self) -> None:
        self._records: list[PostMortem] = []

    def run(
        self,
        thesis_id: str,
        market_id: str,
        direction: str,
        entry_probability: float,
        resolution_probability: float,
        pnl_pct: float,
        agent_predictions: dict[str, float],
    ) -> PostMortem:
        outcome = _classify_outcome(pnl_pct)
        actual = _derive_actual_outcome(direction, outcome)

        broken: list[str] = []
        if outcome == "loss":
            if entry_probability > 0.60 and resolution_probability < 0.40:
                broken.append("overconfident_probability_estimate")
            if abs(entry_probability - resolution_probability) > 0.30:
                broken.append("large_probability_error")

        agent_accuracy = {
            agent: _agent_is_accurate(pred, actual)
            for agent, pred in agent_predictions.items()
        }

        pm = PostMortem(
            thesis_id=thesis_id,
            market_id=market_id,
            direction=direction,
            outcome=outcome,
            actual_outcome=actual,
            entry_probability=entry_probability,
            resolution_probability=resolution_probability,
            pnl_pct=pnl_pct,
            primary_failure=(
                "probability_overestimate"
                if "overconfident_probability_estimate" in broken
                else ""
            ),
            broken_assumptions=broken,
            agent_accuracy=agent_accuracy,
        )
        self._records.append(pm)
        return pm

    def get_all(self) -> list[PostMortem]:
        return list(self._records)
