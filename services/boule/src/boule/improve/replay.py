"""Replay tools — re-run an archived debate's voting math with new weights."""

from __future__ import annotations

from pantheon_core.schema import AgentVote


def reweight_votes(votes: list[AgentVote], weights: dict[str, float]) -> dict[str, float]:
    """Return the weighted-approval share if each vote used the supplied weights."""
    w_total = 0.0
    w_approve = 0.0
    for v in votes:
        if v.vote == "ABSTAIN":
            continue
        w = weights.get(v.agent, 1.0)
        w_total += w
        if v.vote == "APPROVE":
            w_approve += w * v.confidence
    return {
        "weighted_approval": (w_approve / w_total) if w_total > 0 else 0.0,
        "participating_weight": w_total,
    }
