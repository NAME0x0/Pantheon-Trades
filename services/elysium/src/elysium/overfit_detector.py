"""Overfit detector — flags strategies that look great in-sample but degrade OOS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OverfitVerdict:
    overfit: bool
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    degradation: float
    note: str


DEGRADATION_RATIO_LIMIT = 0.4  # OOS Sharpe must be > 40% of IS Sharpe


def detect(in_sample_sharpe: float, out_of_sample_sharpe: float) -> OverfitVerdict:
    if in_sample_sharpe <= 0:
        return OverfitVerdict(
            overfit=False,
            in_sample_sharpe=in_sample_sharpe,
            out_of_sample_sharpe=out_of_sample_sharpe,
            degradation=0.0,
            note="non-positive in-sample Sharpe; cannot evaluate overfit",
        )
    ratio = out_of_sample_sharpe / in_sample_sharpe
    overfit = ratio < DEGRADATION_RATIO_LIMIT
    return OverfitVerdict(
        overfit=overfit,
        in_sample_sharpe=in_sample_sharpe,
        out_of_sample_sharpe=out_of_sample_sharpe,
        degradation=round(1.0 - ratio, 4),
        note=("OOS Sharpe < 40% of IS Sharpe" if overfit else "within tolerance"),
    )
