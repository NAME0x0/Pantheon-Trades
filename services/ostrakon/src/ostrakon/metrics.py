from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now

from ostrakon.brier import brier_score_batch, is_calibrated
from ostrakon.sharpe import sharpe_ratio


@dataclass
class AgentMetrics:
    agent: str
    predictions: list[tuple[float, int]] = field(default_factory=list)
    returns: list[float] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utc_now)

    def add_prediction(self, probability: float, outcome: int, trade_return: float | None = None) -> None:
        self.predictions.append((probability, outcome))
        if trade_return is not None:
            self.returns.append(trade_return)
        self.updated_at = utc_now()

    @property
    def brier(self) -> float:
        return brier_score_batch(self.predictions)

    @property
    def sharpe(self) -> float:
        return sharpe_ratio(self.returns)

    @property
    def calibrated(self) -> bool:
        return is_calibrated(self.brier)

    @property
    def prediction_count(self) -> int:
        return len(self.predictions)

    def credibility_weight(self, baseline: float = 1.0) -> float:
        """Weight fed back to Boule. Scales from 0.5 (poor) to 1.5 (excellent)."""
        if self.prediction_count < 5:
            return baseline
        brier = self.brier
        if brier >= 0.33:
            return 0.5
        if brier <= 0.10:
            return 1.5
        # Linear interpolation between 0.5 and 1.5
        return round(0.5 + (0.33 - brier) / (0.33 - 0.10) * 1.0, 4)
