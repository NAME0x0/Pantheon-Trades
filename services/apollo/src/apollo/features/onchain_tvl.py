"""On-chain feature derivation from DeFiLlama snapshots.

Apollo features are unit-less scores in roughly [0, 1] where possible.
TVL is denominated in dollars, so we convert via either a log-scaled
absolute view (``tvl_log_score``) or a percentile-rank-within-context
view (``tvl_rank_score``).

Inputs are plain dicts to keep the feature module decoupled from the
Pythia source — the runner threads the raw snapshot through.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Anchor points for the log-scaled score:
#   $10M TVL  -> 0.0   (anything below this is uninteresting)
#   $100B TVL -> 1.0   (anything above this maxes out)
LOG_FLOOR = math.log10(1e7)
LOG_CEIL = math.log10(1e11)


@dataclass(frozen=True)
class TvlFeature:
    chain: str
    tvl_usd: float
    log_score: float
    rank_score: float


def tvl_log_score(tvl_usd: float, *, floor_log: float = LOG_FLOOR, ceil_log: float = LOG_CEIL) -> float:
    """Map a raw TVL value to [0, 1] via log-scaling."""
    if tvl_usd <= 0:
        return 0.0
    lg = math.log10(tvl_usd)
    if lg <= floor_log:
        return 0.0
    if lg >= ceil_log:
        return 1.0
    return (lg - floor_log) / (ceil_log - floor_log)


def tvl_rank_score(target_chain: str, chains: list[dict]) -> float:
    """Percentile rank of ``target_chain`` against the supplied chain list."""
    sorted_chains = sorted(
        ((str(c.get("name", "")), float(c.get("tvl", 0) or 0)) for c in chains),
        key=lambda x: x[1],
    )
    if not sorted_chains:
        return 0.0
    n = len(sorted_chains)
    for i, (name, _) in enumerate(sorted_chains):
        if name.lower() == target_chain.lower():
            return (i + 1) / n
    return 0.0


def build_feature(chain: str, chains: list[dict]) -> TvlFeature:
    tvl = 0.0
    for c in chains:
        if str(c.get("name", "")).lower() == chain.lower():
            try:
                tvl = float(c.get("tvl", 0.0))
            except (TypeError, ValueError):
                tvl = 0.0
            break
    return TvlFeature(
        chain=chain,
        tvl_usd=tvl,
        log_score=tvl_log_score(tvl),
        rank_score=tvl_rank_score(chain, chains),
    )


def stablecoin_flow_pct(prev_total: float, curr_total: float) -> float:
    """Signed % change in stablecoin marketcap. Useful catalyst signal."""
    if prev_total <= 0:
        return 0.0
    return (curr_total - prev_total) / prev_total
