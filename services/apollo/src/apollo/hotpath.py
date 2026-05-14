"""Hot-path scorer wrapper — short-circuits scoring under hard latency caps.

Apollo's runner serves a soft real-time loop; when scanning hundreds of
markets per tick we cannot afford to spend the full feature pipeline on
every candidate. The hot-path wrapper:

  1. Pre-filters via ``filters.prefilter`` (cheap).
  2. Pulls cached features from ``precompute`` when fresh.
  3. Falls back to the full ``scorer.score_market`` only when the
     prefilter passes and cached features are missing or stale.
"""

from __future__ import annotations

from collections.abc import Iterable

from pantheon_core.schema import Signal

from apollo.filters import prefilter
from apollo.latency_budget import LatencyBudget
from apollo.precompute import FeatureCache
from apollo.scorer import MarketSnapshot, score_market


def score_with_cache(
    snap: MarketSnapshot,
    cache: FeatureCache,
    budget: LatencyBudget,
) -> Signal | None:
    """Return a Signal or None if the snapshot was filtered/over-budget."""
    if budget.exhausted():
        return None
    verdict = prefilter(snap)
    if not verdict.passed:
        return None
    cached = cache.get(snap.market_id)
    if cached is not None:
        return cached
    with budget.charge():
        sig = score_market(snap)
    cache.put(snap.market_id, sig)
    return sig


def score_batch(
    snapshots: Iterable[MarketSnapshot],
    *,
    cache: FeatureCache,
    budget: LatencyBudget,
) -> list[Signal]:
    out: list[Signal] = []
    for snap in snapshots:
        sig = score_with_cache(snap, cache, budget)
        if sig is not None:
            out.append(sig)
    return out
