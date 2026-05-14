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
