from __future__ import annotations

from datetime import datetime, timezone

from pantheon_core.schema import Signal

from boule.agents.parse_vote import parse_vote


def _make_signal(**kwargs) -> Signal:
    defaults = dict(
        market_id="0xabc",
        question="Will BTC hit 100k?",
        category="crypto",
        market_probability=0.45,
        oracle_probability=0.58,
        edge=0.13,
        edge_abs=0.13,
        band="A",
        band_score=0.72,
        liquidity_score=0.75,
        volatility_score=0.50,
        catalyst_score=0.60,
        sentiment_score=0.55,
        correlation_score=0.50,
        trend_score=0.60,
        volume_24h=120_000,
        open_interest=250_000,
        bid=0.44,
        ask=0.46,
        spread=0.02,
        days_to_resolution=30.0,
        data_sources=["polymarket", "crypto"],
        staleness_seconds=45,
        source_trust_score=0.90,
        pythia_snapshot_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Signal(**defaults)


def test_signal_schema():
    s = _make_signal()
    assert s.band == "A"
    assert s.edge_abs == 0.13


def test_signal_clamps_probability():
    s = _make_signal(market_probability=1.4, oracle_probability=-0.2)
    assert 0.0 <= s.market_probability <= 1.0
    assert 0.0 <= s.oracle_probability <= 1.0


def test_parse_vote_approve():
    text = "VOTE: APPROVE\nCONFIDENCE: 0.80\nPROBABILITY: 0.62\nFLAGS: NONE\nREASON: Strong edge."
    vote, conf, prob, flags = parse_vote(text)
    assert vote == "APPROVE"
    assert conf == 0.80
    assert prob == 0.62
    assert flags == []


def test_parse_vote_reject_with_flags():
    text = "VOTE: REJECT\nCONFIDENCE: 0.90\nPROBABILITY: 0.30\nFLAGS: regulatory_risk, tail_risk\nREASON: Too risky."
    vote, conf, prob, flags = parse_vote(text)
    assert vote == "REJECT"
    assert "regulatory_risk" in flags
    assert "tail_risk" in flags


def test_parse_vote_tolerates_percent():
    text = "VOTE: APPROVE\nCONFIDENCE: 80%\nPROBABILITY: 62%\nFLAGS: NONE"
    vote, conf, prob, _ = parse_vote(text)
    assert vote == "APPROVE"
    assert abs(conf - 0.80) < 1e-6
    assert abs(prob - 0.62) < 1e-6


def test_parse_vote_clamps_out_of_range():
    text = "VOTE: APPROVE\nCONFIDENCE: 1.5\nPROBABILITY: -0.4"
    _, conf, prob, _ = parse_vote(text)
    assert 0.0 <= conf <= 1.0
    assert 0.0 <= prob <= 1.0


def test_parse_vote_garbage_falls_back():
    vote, conf, prob, flags = parse_vote("no structured output here")
    assert vote == "ABSTAIN"
    assert conf == 0.5
    assert prob == 0.5
    assert flags == []
