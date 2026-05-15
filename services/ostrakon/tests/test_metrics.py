from __future__ import annotations

from ostrakon.brier import brier_score, is_calibrated
from ostrakon.sharpe import sharpe_ratio
from ostrakon.metrics import AgentMetrics


def test_brier_perfect():
    assert brier_score(1.0, 1) == 0.0
    assert brier_score(0.0, 0) == 0.0


def test_brier_worst():
    assert brier_score(1.0, 0) == 1.0
    assert brier_score(0.0, 1) == 1.0


def test_brier_random():
    # Random guesser at 0.5 always gets 0.25
    assert brier_score(0.5, 1) == 0.25
    assert brier_score(0.5, 0) == 0.25


def test_calibrated():
    assert is_calibrated(0.15)
    assert not is_calibrated(0.35)


def test_sharpe_positive():
    returns = [0.05, 0.03, 0.06, 0.04, 0.05, 0.07, 0.03]
    s = sharpe_ratio(returns)
    assert s > 0


def test_agent_metrics_credibility():
    m = AgentMetrics(agent="zeus")
    for i in range(10):
        m.add_prediction(0.85, 1, 0.05)
    assert m.brier < 0.25
    assert m.credibility_weight() > 1.0
