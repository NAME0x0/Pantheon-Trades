"""Pre-band filters — cheap rejections applied before band classification.

Every check in this module is a non-LLM, no-network rule. The goal is to
drop obviously-untradeable signals (degenerate spreads, microscopic
liquidity, expired markets) before they consume downstream budget.
"""

from __future__ import annotations

from dataclasses import dataclass

from apollo.scorer import MarketSnapshot


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    reason: str


MIN_VOLUME_24H = 5_000.0
MIN_OPEN_INTEREST = 10_000.0
MAX_SPREAD = 0.20
MIN_PROB = 0.02
MAX_PROB = 0.98
MAX_STALENESS_SECONDS = 1800
MIN_DAYS_TO_RESOLUTION = 0.5


def prefilter(snap: MarketSnapshot) -> FilterResult:
    if snap.volume_24h < MIN_VOLUME_24H:
        return FilterResult(False, f"volume_24h {snap.volume_24h:.0f} < {MIN_VOLUME_24H:.0f}")
    if snap.open_interest < MIN_OPEN_INTEREST:
        return FilterResult(False, f"open_interest {snap.open_interest:.0f} < {MIN_OPEN_INTEREST:.0f}")
    spread = max(0.0, snap.ask - snap.bid)
    if spread > MAX_SPREAD:
        return FilterResult(False, f"spread {spread:.2%} > {MAX_SPREAD:.0%}")
    if not (MIN_PROB <= snap.market_probability <= MAX_PROB):
        return FilterResult(False, f"market_probability {snap.market_probability:.3f} out of range")
    if snap.staleness_seconds > MAX_STALENESS_SECONDS:
        return FilterResult(False, f"staleness {snap.staleness_seconds}s > {MAX_STALENESS_SECONDS}s")
    if snap.days_to_resolution is not None and snap.days_to_resolution < MIN_DAYS_TO_RESOLUTION:
        return FilterResult(False, f"days_to_resolution {snap.days_to_resolution:.2f} too close")
    return FilterResult(True, "ok")
