"""Correlation-aware portfolio sizing.

Two correlated long bets share most of their risk: full-Kelly on each
treats them as independent and silently over-bets. This module
downsizes a new position by a factor of ``(1 - max_corr_with_open)``
where ``max_corr_with_open`` is the largest absolute Pearson
correlation between the new market's signal and any market already
in the open book.

The correlation matrix is supplied by the caller — typically the
gateway reads it from Redis (``strategos:correlation:<m1>:<m2>``) or
computes it on-the-fly from cached price series. This module stays
pure so it's trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationAdjustment:
    raw_size: float
    adjusted_size: float
    max_corr: float
    multiplier: float
    note: str


def correlation_aware_size(
    raw_size_pct: float,
    *,
    market_id: str,
    open_market_ids: list[str],
    pairwise_corr: dict[tuple[str, str], float],
    min_multiplier: float = 0.2,
) -> CorrelationAdjustment:
    """Downsize ``raw_size_pct`` based on correlation with the open book.

    Mechanics:
      1. Look up |corr| between this market and each open market.
      2. max_corr = the largest of those.
      3. multiplier = max(min_multiplier, 1 - max_corr).
      4. adjusted_size = raw_size_pct × multiplier.

    A ``min_multiplier`` floor prevents perfectly correlated new bets
    from being sized to zero — that case is better handled upstream
    via a "do not duplicate exposure" gate.
    """
    if not open_market_ids:
        return CorrelationAdjustment(
            raw_size=raw_size_pct,
            adjusted_size=raw_size_pct,
            max_corr=0.0,
            multiplier=1.0,
            note="empty_book",
        )

    max_corr = 0.0
    pair: tuple[str, str] | None = None
    for other in open_market_ids:
        c = _lookup(pairwise_corr, market_id, other)
        if c is None:
            continue
        if abs(c) > max_corr:
            max_corr = abs(c)
            pair = (market_id, other)

    multiplier = max(min_multiplier, 1.0 - max_corr)
    adjusted = raw_size_pct * multiplier
    note = (
        f"max_corr_with={pair[1]}:{max_corr:.2f}"
        if pair is not None
        else "no_corr_data"
    )
    return CorrelationAdjustment(
        raw_size=raw_size_pct,
        adjusted_size=adjusted,
        max_corr=max_corr,
        multiplier=multiplier,
        note=note,
    )


def _lookup(matrix: dict[tuple[str, str], float], a: str, b: str) -> float | None:
    """Bidirectional lookup so callers can store the matrix unidirectionally."""
    if (a, b) in matrix:
        return float(matrix[(a, b)])
    if (b, a) in matrix:
        return float(matrix[(b, a)])
    return None
