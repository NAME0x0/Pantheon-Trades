"""Correlation feature — how independent this market is from existing positions.

A *high* correlation score is *good* in the band-score sense: it means the
candidate adds true diversification (low correlation to existing book). We
implement this by taking the maximum absolute correlation against any open
position and returning ``1 - max_abs_corr``. A candidate that perfectly
duplicates an open position scores 0; an orthogonal one scores 1.
"""

from __future__ import annotations


def correlation_score(open_position_correlations: list[float] | None = None) -> float:
    """Diversification score in [0, 1].

    ``open_position_correlations`` is a list of correlation coefficients (in
    [-1, 1]) between this candidate and each currently open position. An
    empty list (no open positions) returns 1.0 — full diversification.
    """
    if not open_position_correlations:
        return 1.0
    max_abs = max(min(abs(c), 1.0) for c in open_position_correlations)
    return round(1.0 - max_abs, 6)
