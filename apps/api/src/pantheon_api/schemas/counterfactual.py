"""Counterfactual summary response."""

from __future__ import annotations

from pydantic import BaseModel


class CounterfactualSummary(BaseModel):
    label: str
    n_trades: int
    realised_pnl_usdc: float
    counterfactual_pnl_usdc: float
    delta_pnl_usdc: float
