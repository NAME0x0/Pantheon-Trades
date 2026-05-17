"""Kelly position sizing for binary prediction-market contracts.

For a YES contract bought at price ``q`` that pays $1 on YES resolution and $0
on NO, the canonical Kelly fraction when our subjective probability of YES
is ``p*`` is::

    f* = (p* - q) / (1 - q)

The numerator is the edge in probability space. The denominator is the
amount lost per dollar on the unfavourable outcome (price). The same formula
works for a NO contract — just flip ``q`` to ``1 - q`` and use ``1 - p*``.

We **never** use full Kelly. The Pantheon constitution mandates half-Kelly,
capped at ``MAX_POSITION_PCT`` of book equity, and we refuse to open any
position smaller than ``MIN_POSITION_THRESHOLD`` because the gas/slippage
floor makes microscopic trades net-negative.

The caller passes the *directional* edge (always >= 0 for an actionable
thesis) plus the price actually being paid for the chosen side. That keeps
this module agnostic to YES/NO orientation.
"""

from __future__ import annotations

KELLY_FRACTION = 0.5  # half-Kelly only — see CONSTITUTION
DEFAULT_MAX_PCT = 0.05
DEFAULT_MIN_THRESHOLD = 0.005


def full_kelly(directional_edge: float, entry_price: float) -> float:
    """Pure Kelly for a binary contract paying $1 on win.

    ``directional_edge`` must be the magnitude of the alpha (>= 0).
    ``entry_price`` is what the contract trades at on the side we are buying;
    degenerate prices (<=0 or >=1) collapse to zero — Kelly diverges and we
    refuse to size on a market that quotes that aggressively anyway.
    """
    if directional_edge <= 0:
        return 0.0
    if not (0.0 < entry_price < 1.0):
        return 0.0
    loss_per_dollar = 1.0 - entry_price
    f = directional_edge / loss_per_dollar
    if f < 0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def half_kelly(directional_edge: float, entry_price: float) -> float:
    return full_kelly(directional_edge, entry_price) * KELLY_FRACTION


def size_position(
    directional_edge: float,
    entry_price: float,
    max_pct: float = DEFAULT_MAX_PCT,
    min_threshold: float = DEFAULT_MIN_THRESHOLD,
) -> tuple[float, float, str]:
    """Return ``(final_size_pct, kelly_fraction, reason)``.

    ``reason`` is one of:
        - ``"ok"`` — half-Kelly fits inside the cap and clears the floor.
        - ``"capped"`` — half-Kelly exceeded ``max_pct``; clipped.
        - ``"sub_threshold"`` — half-Kelly below the minimum-position floor.
        - ``"no_edge"`` — non-positive directional edge or degenerate price.
    """
    if directional_edge <= 0 or not (0.0 < entry_price < 1.0):
        return 0.0, 0.0, "no_edge"

    fk = full_kelly(directional_edge, entry_price)
    hk = fk * KELLY_FRACTION

    if hk < min_threshold:
        return 0.0, fk, "sub_threshold"

    if hk > max_pct:
        return max_pct, fk, "capped"

    return hk, fk, "ok"


def size_position_conformal(
    council_p_point: float,
    market_p: float,
    direction: str,
    *,
    q_hat: float,
    alpha: float = 0.10,
    max_pct: float = DEFAULT_MAX_PCT,
    min_threshold: float = DEFAULT_MIN_THRESHOLD,
) -> tuple[float, float, str, dict[str, float]]:
    """Half-Kelly sizing against the CONFORMAL LOWER BOUND of the
    council probability, not the point estimate.

    The point estimate is sharpest in expectation but most fragile at
    the extremes — over-sizing on a p=0.95 prediction when the true
    probability is 0.85 is the classic Kelly blow-up. Sizing against
    ``p_lo`` (conformal lower bound) gives natural overconfidence
    regularisation that widens the interval exactly where calibration
    data is thinnest. Our backtest confirms the council's tails are
    over-confident relative to Manifold consensus.

    Args:
        council_p_point: point-estimate council probability of YES.
        market_p: implied market probability of YES.
        direction: ``"YES"`` or ``"NO"``.
        q_hat: conformal half-width. Operator fits this from settled
            trades via ``ostrakon.conformal_calibration.split_quantile``
            and passes the value here. We don't import ostrakon to
            keep areopagus self-contained.
        alpha: nominal miscoverage rate (for diagnostics only — the
            arithmetic uses ``q_hat`` directly).
        max_pct, min_threshold: same as ``size_position``.

    Returns:
        ``(final_size_pct, kelly_fraction, reason, diagnostics)``
        where ``diagnostics`` has ``p_lo``, ``p_hi``, ``p_used``,
        ``edge_point``, ``edge_conservative``.
    """
    if direction not in ("YES", "NO"):
        raise ValueError(f"direction must be YES or NO; got {direction}")

    # Build the conformal interval inline (matches
    # ostrakon.conformal_calibration.interval exactly).
    p_clamped = max(0.0, min(1.0, float(council_p_point)))
    p_lo = max(0.0, p_clamped - q_hat)
    p_hi = min(1.0, p_clamped + q_hat)

    # Conservative p on the trade's side.
    p_used = p_lo if direction == "YES" else (1.0 - p_hi)

    # Directional edge using the conservative p.
    if direction == "YES":
        entry = market_p
        edge_conservative = max(0.0, p_used - market_p)
        edge_point = max(0.0, p_clamped - market_p)
    else:
        entry = 1.0 - market_p
        edge_conservative = max(0.0, p_used - (1.0 - market_p))
        edge_point = max(0.0, (1.0 - p_clamped) - (1.0 - market_p))

    final_pct, kelly_f, reason = size_position(
        directional_edge=edge_conservative,
        entry_price=entry,
        max_pct=max_pct,
        min_threshold=min_threshold,
    )
    diagnostics = {
        "p_lo": p_lo,
        "p_hi": p_hi,
        "p_point": p_clamped,
        "p_used_for_kelly": p_used,
        "edge_point": edge_point,
        "edge_conservative": edge_conservative,
        "q_hat": q_hat,
        "alpha": alpha,
    }
    return final_pct, kelly_f, reason, diagnostics
