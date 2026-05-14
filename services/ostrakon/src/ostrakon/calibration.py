"""Calibration helpers — reliability diagrams + expected calibration error."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_confidence: float
    empirical_rate: float


def bin_predictions(
    predictions: list[tuple[float, int]],
    n_bins: int = 10,
) -> list[CalibrationBin]:
    if not predictions:
        return []
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    width = 1.0 / n_bins
    for prob, outcome in predictions:
        idx = min(int(prob / width), n_bins - 1)
        bins[idx].append((prob, outcome))
    out: list[CalibrationBin] = []
    for i, bucket in enumerate(bins):
        if not bucket:
            continue
        mean_conf = sum(p for p, _ in bucket) / len(bucket)
        rate = sum(o for _, o in bucket) / len(bucket)
        out.append(
            CalibrationBin(
                lower=i * width,
                upper=(i + 1) * width,
                count=len(bucket),
                mean_confidence=round(mean_conf, 4),
                empirical_rate=round(rate, 4),
            )
        )
    return out


def expected_calibration_error(predictions: list[tuple[float, int]]) -> float:
    if not predictions:
        return 0.0
    bins = bin_predictions(predictions)
    total = sum(b.count for b in bins) or 1
    return round(
        sum(b.count * abs(b.mean_confidence - b.empirical_rate) for b in bins) / total,
        4,
    )
