"""Penalty schedule — multiplicative weight cuts for missteps."""

from __future__ import annotations


PENALTY_HALLUCINATION = 0.85
PENALTY_OVERCONFIDENT_LOSS = 0.90
PENALTY_CONSTITUTIONAL_BREACH = 0.50


def apply_penalty(current_weight: float, kind: str) -> float:
    """Multiplicative penalty; never drops below 0.1."""
    factor = {
        "hallucination": PENALTY_HALLUCINATION,
        "overconfident_loss": PENALTY_OVERCONFIDENT_LOSS,
        "constitutional_breach": PENALTY_CONSTITUTIONAL_BREACH,
    }.get(kind, 1.0)
    return max(0.1, round(current_weight * factor, 4))
