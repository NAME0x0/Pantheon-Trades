"""Brier-weighted council aggregation.

The XML backtest showed council aggregation (5-role mean) closes 80%
of the Gemini-vs-Manifold Brier gap. The naive aggregator weights all
roles equally. The empirical Brier per role on past markets tells us
which roles actually deserve their voice — well-calibrated roles
should weigh more than miscalibrated ones.

This module computes per-agent weights from realised Brier scores
on a held-out sample, then aggregates a council vote as a Brier-
weighted mean of agent probabilities.

Returns weights such that:

  - Every agent gets a positive weight (no zero-weight agents).
  - Better-calibrated agents (lower Brier) get exponentially more
    weight than worse-calibrated agents.
  - Tunable temperature ``tau`` controls how sharply the weights
    favour the best agent: high tau → near-uniform, low tau → nearly
    winner-take-all.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentVote:
    """One agent's probability estimate on one market."""

    agent: str
    probability: float


@dataclass
class CouncilWeights:
    """Per-agent weights computed from realised Brier."""

    weights: dict[str, float] = field(default_factory=dict)
    briers: dict[str, float] = field(default_factory=dict)
    sample_counts: dict[str, int] = field(default_factory=dict)
    tau: float = 0.05


def compute_briers(
    history: list[dict],
) -> tuple[dict[str, float], dict[str, int]]:
    """Mean Brier score per agent across a settled-trade history.

    ``history`` is a list of dicts with at least ``agent``,
    ``probability_estimate``, and ``outcome`` (0/1).
    """
    sq_errors: dict[str, list[float]] = defaultdict(list)
    for r in history:
        agent = r.get("agent")
        if not agent:
            continue
        try:
            p = float(r["probability_estimate"])
            o = int(r["outcome"])
        except (KeyError, TypeError, ValueError):
            continue
        sq_errors[agent].append((p - o) ** 2)
    briers: dict[str, float] = {}
    counts: dict[str, int] = {}
    for agent, errs in sq_errors.items():
        if not errs:
            continue
        briers[agent] = sum(errs) / len(errs)
        counts[agent] = len(errs)
    return briers, counts


def compute_weights(
    briers: dict[str, float],
    *,
    tau: float = 0.05,
    floor: float = 0.05,
) -> dict[str, float]:
    """Softmax over -Brier with temperature ``tau``.

    Lower Brier → higher weight. ``floor`` is the minimum weight per
    agent (post-softmax) so no agent is silenced — empirical Brier
    on small samples is noisy and we don't want to discard agents
    too aggressively.
    """
    if not briers:
        return {}
    # We want weights ∝ exp(-brier / tau).
    inv = {a: -b / max(tau, 1e-6) for a, b in briers.items()}
    max_logit = max(inv.values())
    exps = {a: math.exp(logit - max_logit) for a, logit in inv.items()}
    total = sum(exps.values()) or 1.0
    raw = {a: e / total for a, e in exps.items()}
    # Apply floor: shift all up by ``floor`` then renormalise.
    shifted = {a: w + floor for a, w in raw.items()}
    total_shifted = sum(shifted.values())
    return {a: w / total_shifted for a, w in shifted.items()}


def fit_weights(
    history: list[dict],
    *,
    tau: float = 0.05,
    floor: float = 0.05,
) -> CouncilWeights:
    """End-to-end fit from history → CouncilWeights."""
    briers, counts = compute_briers(history)
    weights = compute_weights(briers, tau=tau, floor=floor)
    return CouncilWeights(
        weights=weights,
        briers=briers,
        sample_counts=counts,
        tau=tau,
    )


def aggregate(
    votes: list[AgentVote],
    weights: CouncilWeights | None = None,
) -> float:
    """Brier-weighted mean of agent probabilities.

    Missing weights → uniform weight (1/N). Probabilities clamped to
    [0.01, 0.99] before averaging to avoid log-domain blowup downstream.
    """
    if not votes:
        return 0.5
    if weights is None or not weights.weights:
        # Fall back to uniform mean.
        return sum(max(0.01, min(0.99, v.probability)) for v in votes) / len(votes)
    weighted_sum = 0.0
    weight_total = 0.0
    for v in votes:
        w = weights.weights.get(v.agent, 1.0 / len(votes))
        p = max(0.01, min(0.99, v.probability))
        weighted_sum += w * p
        weight_total += w
    if weight_total <= 0:
        return sum(max(0.01, min(0.99, v.probability)) for v in votes) / len(votes)
    return weighted_sum / weight_total


def diversity(votes: list[AgentVote]) -> float:
    """Standard deviation of probabilities across the council.

    Useful for flagging low-conviction (low diversity ⇒ groupthink) or
    high-disagreement (high diversity ⇒ widen sizing buffer) regimes.
    """
    if len(votes) < 2:
        return 0.0
    probs = [v.probability for v in votes]
    mu = sum(probs) / len(probs)
    var = sum((p - mu) ** 2 for p in probs) / max(1, len(probs) - 1)
    return math.sqrt(var)
