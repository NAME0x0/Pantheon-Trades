"""Anti-Goodhart diversity metric for the council.

Brier-score-driven agent calibration creates a subtle pressure for
agents to converge on each other — the agent that mirrors the median
always scores better than the loner. Over time the council collapses
to a single voice, which destroys the deliberation's value.

We track two diversity statistics per round-4 vote distribution:

  - **Shannon entropy** over the {APPROVE, REJECT, ABSTAIN} histogram.
    Maxes at log2(3) ≈ 1.585 when all three labels are equally
    represented; 0 when every agent says the same thing.

  - **Probability-spread** standard deviation across the agents'
    individual probability estimates. Low std = "all 9 say 0.62" =
    fake consensus.

A composite score in [0, 1] is exposed so callers (Boule, Olympus)
can alert when the council collapses below a threshold.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence

MIN_DIVERSITY = 0.35  # below this → council is collapsing


@dataclass(frozen=True)
class DiversitySnapshot:
    vote_entropy: float        # bits of label-distribution entropy
    probability_std: float     # std of probability estimates (APPROVE+REJECT voters)
    composite: float           # 0..1 — higher = more diverse
    alert: bool                # True when composite < MIN_DIVERSITY


def _shannon_entropy(counts: Iterable[int]) -> float:
    counts = [c for c in counts if c > 0]
    if not counts:
        return 0.0
    total = sum(counts)
    return -sum((c / total) * math.log2(c / total) for c in counts)


def measure(
    votes: Sequence[tuple[str, float]],
    *,
    min_diversity: float = MIN_DIVERSITY,
) -> DiversitySnapshot:
    """Compute diversity stats for a single deliberation's votes.

    ``votes`` is a list of (vote_label, probability_estimate). Pass
    every agent's vote. ABSTAIN votes count toward the entropy but
    their probability is excluded from the std (it's a non-vote).
    """
    counts = {"APPROVE": 0, "REJECT": 0, "ABSTAIN": 0}
    probs: list[float] = []
    for label, p in votes:
        if label in counts:
            counts[label] += 1
        if label != "ABSTAIN":
            probs.append(float(p))

    entropy = _shannon_entropy(counts.values())
    # Normalise to [0, 1] against the max possible entropy of 3 labels.
    entropy_norm = entropy / math.log2(3) if entropy > 0 else 0.0

    if len(probs) >= 2:
        try:
            std = statistics.pstdev(probs)
        except statistics.StatisticsError:
            std = 0.0
    else:
        std = 0.0
    # Probability std up to ~0.5 in the worst case (votes 0 and 1).
    std_norm = min(1.0, std / 0.25)

    # 60% entropy, 40% probability spread — entropy is the harder
    # signal to game so it dominates.
    composite = 0.6 * entropy_norm + 0.4 * std_norm
    return DiversitySnapshot(
        vote_entropy=round(entropy, 4),
        probability_std=round(std, 4),
        composite=round(composite, 4),
        alert=composite < min_diversity,
    )
