"""Banishment thresholds — when an agent should be exiled."""

from __future__ import annotations

from dataclasses import dataclass


BAN_BRIER_THRESHOLD = 0.40
BAN_MIN_PREDICTIONS = 10
BAN_CALIBRATION_THRESHOLD = 0.30


@dataclass(frozen=True)
class BanishmentVerdict:
    banish: bool
    reason: str


def should_banish(
    brier: float,
    prediction_count: int,
    calibration_error: float,
) -> BanishmentVerdict:
    if prediction_count < BAN_MIN_PREDICTIONS:
        return BanishmentVerdict(False, "below minimum prediction count")
    if brier >= BAN_BRIER_THRESHOLD:
        return BanishmentVerdict(True, f"Brier {brier:.3f} >= {BAN_BRIER_THRESHOLD}")
    if calibration_error >= BAN_CALIBRATION_THRESHOLD:
        return BanishmentVerdict(
            True, f"ECE {calibration_error:.3f} >= {BAN_CALIBRATION_THRESHOLD}"
        )
    return BanishmentVerdict(False, "within tolerances")
