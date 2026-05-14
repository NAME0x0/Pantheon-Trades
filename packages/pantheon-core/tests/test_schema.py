from __future__ import annotations

from datetime import datetime, timezone

from pantheon_core.direction import (
    directional_edge,
    entry_price,
    infer_direction,
)
from pantheon_core.schema import AgentVote, Signal, utc_now


def test_utc_now_is_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 0


def test_signal_clamps_probabilities():
    s = Signal(
        market_id="m",
        question="?",
        category="crypto",
        market_probability=1.5,
        oracle_probability=-0.2,
        edge=0.1,
        edge_abs=-0.1,
        band="A",
        band_score=0.7,
        liquidity_score=2.0,
        volatility_score=0.5,
        catalyst_score=0.5,
        sentiment_score=0.5,
        correlation_score=0.5,
        trend_score=0.5,
        volume_24h=100,
        open_interest=100,
        bid=0.3,
        ask=0.4,
        spread=0.1,
        data_sources=[],
        staleness_seconds=10,
        source_trust_score=0.9,
        pythia_snapshot_at=datetime.now(timezone.utc),
    )
    assert 0.0 <= s.market_probability <= 1.0
    assert 0.0 <= s.oracle_probability <= 1.0
    assert s.liquidity_score == 1.0
    assert s.edge_abs == 0.1  # validator coerces to non-negative


def test_agent_vote_clamps():
    v = AgentVote(
        agent="ares",
        vote="APPROVE",
        confidence=1.4,
        probability_estimate=-0.5,
        summary="x",
    )
    assert v.confidence == 1.0
    assert v.probability_estimate == 0.0


def test_infer_direction_yes():
    assert infer_direction(0.40, 0.55) == "YES"
    assert infer_direction(0.60, 0.40) == "NO"


def test_directional_edge_is_positive_when_actionable():
    assert directional_edge(0.40, 0.55, "YES") > 0
    assert directional_edge(0.60, 0.40, "NO") > 0


def test_entry_price_orientation():
    assert entry_price(0.40, "YES") == 0.40
    assert abs(entry_price(0.40, "NO") - 0.60) < 1e-9
