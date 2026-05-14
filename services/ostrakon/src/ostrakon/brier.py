from __future__ import annotations


def brier_score(probability: float, outcome: int) -> float:
    """Brier score for a single prediction. outcome: 1=YES resolved, 0=NO resolved."""
    return (probability - outcome) ** 2


def brier_score_batch(predictions: list[tuple[float, int]]) -> float:
    """Mean Brier score over a list of (probability, outcome) pairs."""
    if not predictions:
        return 0.0
    return sum(brier_score(p, o) for p, o in predictions) / len(predictions)


def is_calibrated(brier: float, threshold: float = 0.25) -> bool:
    """Agent is well-calibrated if Brier score < threshold (0.33 = random)."""
    return brier < threshold
