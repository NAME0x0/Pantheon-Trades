from __future__ import annotations


def compute_edge(oracle_probability: float, market_probability: float) -> tuple[float, float]:
    """Returns (edge, edge_abs)."""
    edge = oracle_probability - market_probability
    return round(edge, 6), round(abs(edge), 6)


def oracle_probability(
    base_prob: float,
    sentiment_adj: float,
    trend_adj: float,
    catalyst_adj: float,
    calibration_factor: float = 1.0,
) -> float:
    """
    Blend adjustments into oracle probability.
    All adjustments are additive deltas in probability space, clamped to [0.02, 0.98].
    """
    p = base_prob + sentiment_adj + trend_adj + catalyst_adj
    p = p * calibration_factor
    return round(max(0.02, min(0.98, p)), 6)
