"""Cross-venue consensus-delta feature.

Combines two prior-probability sources for the same question:

  * Polymarket's order-book implied (already in the Signal).
  * Manifold Markets' play-money implied (free, public API).

The *delta* between the two priors is a calibration signal — not
direct alpha. When the gap is wide, *we don't size bigger*; we
*demand more confidence from the council* before sizing at all.

This module is pure math. Pythia's ``ManifoldSource`` supplies the
Manifold-side probability; we turn the gap into a flag + a sizing
multiplier that Areopagus can read.
"""

from __future__ import annotations

from dataclasses import dataclass

# When the gap exceeds this, we treat the trade as 'wide-disagreement'
# and the council should be more skeptical, not more aggressive.
WIDE_GAP_THRESHOLD = 0.15  # absolute probability points


@dataclass(frozen=True)
class ConsensusDeltaFeature:
    manifold_p: float | None
    polymarket_p: float
    delta: float | None         # manifold_p - polymarket_p
    abs_delta: float | None     # |delta|
    wide_disagreement: bool     # |delta| >= WIDE_GAP_THRESHOLD
    sizing_multiplier: float    # 0..1 cap applied to recommended size


def sizing_multiplier(delta: float | None) -> float:
    """Compute a sizing cap from the delta.

    No data → 1.0 (no effect). Small gap (< 0.05) → 1.0. Medium gap
    (0.05 – 0.15) → linear ramp down to 0.7. Wide gap (> 0.15) →
    saturates at 0.5.

    The intent is not to penalise — it is to *force the council to
    take the disagreement seriously*. A 30pp gap between two priors
    means somebody is wildly wrong, and you don't want a full half-
    Kelly bet on the side of the dispute.
    """
    if delta is None:
        return 1.0
    a = abs(delta)
    if a < 0.05:
        return 1.0
    if a >= WIDE_GAP_THRESHOLD:
        return 0.5
    # Linear interpolate between (0.05, 1.0) and (0.15, 0.7).
    return 1.0 - 3.0 * (a - 0.05)


def compose(
    *,
    polymarket_p: float,
    manifold_p: float | None,
) -> ConsensusDeltaFeature:
    if manifold_p is None:
        return ConsensusDeltaFeature(
            manifold_p=None,
            polymarket_p=polymarket_p,
            delta=None,
            abs_delta=None,
            wide_disagreement=False,
            sizing_multiplier=1.0,
        )
    d = manifold_p - polymarket_p
    abs_d = abs(d)
    return ConsensusDeltaFeature(
        manifold_p=manifold_p,
        polymarket_p=polymarket_p,
        delta=d,
        abs_delta=abs_d,
        wide_disagreement=abs_d >= WIDE_GAP_THRESHOLD,
        sizing_multiplier=sizing_multiplier(d),
    )
