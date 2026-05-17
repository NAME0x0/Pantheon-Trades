"""Build curated demo trace bundles for the marketing site.

Four scenarios, all run real Areopagus + Strategos logic. Only the
agent dialogue is curated (mirrors what observed live Gemini runs
produced — see prior session logs in the repo history).

  1. btc-120k-approve.json     — crypto, full council APPROVE, paper trade fills
  2. btc-120k-restraint.json   — crypto, Zeus early VETO, Proof of Restraint witness
  3. election-2028-approve.json — politics, NO direction, council APPROVE with Themis resize
  4. nfl-superbowl-restraint.json — sports, low-liquidity rejection by Solon (Article IV)

Run:
    uv run python tests/build_demo_traces.py
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "boule" / "src",
    ROOT / "services" / "areopagus" / "src",
    ROOT / "services" / "strategos" / "src",
):
    sys.path.insert(0, str(p))

from apollo.features.catalyst import CatalystEvent
from apollo.features.sentiment import SentimentSample
from apollo.scorer import MarketSnapshot, score_market
from areopagus.court import AreopagusCourt
from areopagus.gates import PortfolioState
from pantheon_core.schema import (
    AgentVote,
    ApprovalToken,
    ExitConditions,
    Thesis,
    ThesisBlock,
    TraceEvent,
)
from strategos.paper import PaperBook


def _build_signal():
    snap = MarketSnapshot(
        market_id="0xpantheon_demo_btc_120k",
        question="Will Bitcoin close above $120,000 by 2026-12-31?",
        category="crypto",
        market_probability=0.42,
        bid=0.41,
        ask=0.43,
        volume_24h=580_000,
        open_interest=1_400_000,
        price_history=[0.30, 0.32, 0.35, 0.38, 0.39, 0.40, 0.41, 0.42, 0.43, 0.42],
        price_std_24h=0.045,
        price_mean=0.39,
        catalysts=[
            CatalystEvent("Fed FOMC rate decision", 36.0, 0.85),
            CatalystEvent("BTC quarterly options expiry", 96.0, 0.55),
        ],
        sentiment_samples=[
            SentimentSample(polarity=0.6, weight=3.0),
            SentimentSample(polarity=0.4, weight=2.0),
            SentimentSample(polarity=-0.2, weight=1.5),
        ],
        data_sources=["polymarket_sim", "coingecko_sim", "news_sim"],
        snapshot_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        staleness_seconds=20,
        source_trust_score=0.92,
        resolution_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
        days_to_resolution=230.0,
        sentiment_adjustment=0.08,
        trend_adjustment=0.05,
        catalyst_adjustment=0.04,
    )
    return score_market(snap)


# ──────────────────────────────────────────────────────────────────────
# Curated agent dialogue. Patterned on observed Gemini outputs.
# ──────────────────────────────────────────────────────────────────────

AGENTS = [
    ("ares", 1.0, "Bull"),
    ("hades", 1.0, "Bull"),
    ("athena", 1.2, "Bear"),
    ("cassandra", 1.0, "Bear"),
    ("solon", 1.5, "Risk"),       # has veto
    ("zeus", 2.0, "Risk"),         # has veto
    ("themis", 1.0, "Risk"),
    ("hephaestus", 1.0, "Execution"),
    ("daedalus", 1.0, "Execution"),
    ("humans", 1.0, "Execution"),
]

OPENINGS_APPROVE = {
    "ares": "Strong asymmetric long here. Market prices 42% but the trend regression, sentiment momentum, and FOMC catalyst all point higher. Edge +17pp is real. Conviction: LONG.",
    "hades": "Liquidity is deep ($580k 24h volume, $1.4M OI). Spread 2% is tight enough to size. Downside is bounded by the 0.30 floor in 30-day price history — I see no fat tail risk that the consensus is missing.",
    "athena": "I'll steelman bear case: BTC has rejected $100k twice in 2025. To clear $120k by year-end requires ~25% upside from spot. Resolution date 230 days out — plenty of vol but also plenty of headline risk.",
    "cassandra": "Catalyst landscape is mixed. FOMC 36hrs out is +0.85 weight but BTC quarterly opex is gamma-neutral. Sentiment skew is bullish but small sample (3 sources). Watch staleness — 20s is acceptable but degrading.",
    "solon": "Constitutional check: position size proposal must respect MAX_POSITION_PCT 5%. Half-Kelly on 17pp edge at 0.42 entry gives ~7.5% raw — will need resize. No quorum violations, no banned market category.",
    "zeus": "Risk gates: edge band B is acceptable. Liquidity floor cleared. No correlation cluster violation (only crypto exposure currently). No restraint trigger. I will not veto.",
    "themis": "Procedural review: signal age 20s, oracle/market separation maintained, no double-counting in catalyst features. Trace integrity ok. Proceed.",
    "hephaestus": "Execution plan: target 5% NAV (post-resize), entry at mid 0.42, slippage budget 50bps. Depth $580k will absorb $500 with negligible impact. Exit conditions: stop at 0.37, target at 0.69.",
    "daedalus": "Strategy fit: this is a directional momentum trade with catalyst tailwind. Half-Kelly sizing appropriate. No need for hedge leg given low correlation to existing book.",
    "humans": "Crowd sentiment is leaning bullish but not euphoric. Funding rates moderate. No retail FOMO signal. This is a thoughtful position, not a meme trade. Approve.",
}

OPENINGS_VETO = {
    "zeus": "CONSTITUTIONAL VIOLATION. The proposed sizing implies stacking crypto correlation beyond risk_policy.crypto_cluster_max. Combined with existing book exposure this breaches Article III §2. VETO. No further deliberation required.",
    "ares": "Bull case present but Zeus has flagged a cluster violation — I defer to risk authority.",
    "hades": "Conceding to Zeus. Will revisit once correlation envelope clears.",
    "athena": "(deferred — Zeus veto active)",
    "cassandra": "(deferred — Zeus veto active)",
    "solon": "Confirming Zeus reading. Cluster cap is hard, not advisory. Restraint witness should be written.",
    "themis": "(deferred)",
    "hephaestus": "(deferred)",
    "daedalus": "(deferred)",
    "humans": "(deferred)",
}

CHALLENGES = {
    "ares": "Athena raises a fair structural point — $100k has been a rejection level twice. But each rejection saw progressively higher lows. Higher lows in a multi-year uptrend is the bull thesis intact, not invalidated.",
    "hades": "Cassandra is right that the catalyst signal is mixed. I'd narrow my conviction: this is a slow-bleed thesis, not a vol-pop. Sizing should reflect a 60-90 day hold, not a week.",
    "athena": "Reading Ares's reply — agreed that higher lows are bullish. My remaining concern: 230 days to resolution. Lots of room for an unexpected macro shock to dominate the path.",
    "cassandra": "I'll temper my earlier skepticism. Source trust 0.92 is high, and three sources is sufficient for a B-band signal. Risk-of-ruin is bounded by sizing, not data quality.",
    "solon": "Reviewing the resize math: 7.5% raw → 5% cap. That's the right transformation. No change.",
    "zeus": "All challenges resolved within risk envelope. No reason to elevate to veto.",
    "themis": "Procedural integrity maintained across challenges.",
    "hephaestus": "Updated exit plan based on Hades's 60-90 day reframe: extend max_hold_days to 90, keep stop at 0.37.",
    "daedalus": "Confirming no hedge required. Half-Kelly inside cluster limit.",
    "humans": "No new flags. Sentiment stable.",
}

VOTES_APPROVE = [
    ("ares", "APPROVE", 0.85, 0.62, []),
    ("hades", "APPROVE", 0.80, 0.60, []),
    ("athena", "APPROVE", 0.70, 0.55, []),
    ("cassandra", "APPROVE", 0.65, 0.54, []),
    ("solon", "APPROVE", 0.90, 0.59, []),
    ("zeus", "APPROVE", 1.00, 0.59, []),
    ("themis", "APPROVE", 0.85, 0.59, []),
    ("hephaestus", "APPROVE", 0.85, 0.60, []),
    ("daedalus", "APPROVE", 0.85, 0.59, []),
    ("humans", "APPROVE", 0.80, 0.58, []),
]


def _emit_event(events, *, seq, trace_id, thesis_id, signal_id, market_id, event_type, content,
                agent=None, round=None, tokens=None, latency_ms=None, vote=None,
                confidence=None, probability_estimate=None, flags=None, timestamp=None):
    ev = TraceEvent(
        trace_id=trace_id,
        thesis_id=thesis_id,
        signal_id=signal_id,
        market_id=market_id,
        event_type=event_type,  # type: ignore[arg-type]
        agent=agent,
        round=round,
        content=content,
        tokens=tokens,
        latency_ms=latency_ms,
        vote=vote,  # type: ignore[arg-type]
        confidence=confidence,
        probability_estimate=probability_estimate,
        flags=flags or [],
        timestamp=timestamp or datetime.now(timezone.utc),
        sequence=seq,
    )
    events.append(ev)


def _build_approve_bundle():
    signal = _build_signal()
    thesis_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    t0 = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

    events: list[TraceEvent] = []
    seq = 0
    blocks: list[ThesisBlock] = []

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    def push(**kw):
        _emit_event(events, seq=next_seq(), trace_id=trace_id, thesis_id=thesis_id,
                    signal_id=signal.signal_id, market_id=signal.market_id, **kw)

    push(event_type="deliberation_start",
         content=f"Market {signal.market_id} | edge {signal.edge:+.2%} | band {signal.band}",
         timestamp=t0)

    # Round 1
    push(event_type="agent_round_start", content="Round 1 — openings", round=1, timestamp=t0 + timedelta(seconds=1))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = OPENINGS_APPROVE[name]
        latency = 1200 + i * 80
        tokens = 180 + i * 12
        ts = t0 + timedelta(seconds=2 + i * 3)
        push(event_type="agent_output", content=text, agent=name, round=1,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=1, content=text, tokens=tokens, latency_ms=latency))

    # Round 2
    push(event_type="agent_round_start", content="Round 2 — challenges", round=2,
         timestamp=t0 + timedelta(seconds=33))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = CHALLENGES[name]
        latency = 1100 + i * 70
        tokens = 140 + i * 9
        ts = t0 + timedelta(seconds=34 + i * 3)
        push(event_type="agent_output", content=text, agent=name, round=2,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=2, content=text, tokens=tokens, latency_ms=latency))

    # Round 3 — Athena synthesis
    synth = (
        "Synthesis: 10/10 council members approve. The bull case (Ares, Hades) is "
        "structural — higher lows in a multi-year uptrend with deep liquidity. "
        "The bear case (myself, Cassandra) acknowledged but bounded by sizing. "
        "Risk authority (Zeus, Solon) found no constitutional violation. "
        "Execution (Hephaestus, Daedalus, Humans) confirms 5% NAV is the right size "
        "post half-Kelly resize. Recommended action: LONG YES at 0.42 with 60-90 day hold, "
        "target 0.69, stop 0.37."
    )
    push(event_type="synthesis", content=synth, agent="athena", round=3,
         timestamp=t0 + timedelta(seconds=65))
    blocks.append(ThesisBlock(agent="athena", round=3, content=synth, tokens=260, latency_ms=2100))

    # Round 4 — votes
    push(event_type="agent_round_start", content="Round 4 — votes", round=4,
         timestamp=t0 + timedelta(seconds=67))
    votes: list[AgentVote] = []
    for i, (name, vote, conf, prob, flags) in enumerate(VOTES_APPROVE):
        ts = t0 + timedelta(seconds=68 + i * 2)
        push(event_type="vote", content=f"{name}: {vote} p={prob:.2f} c={conf:.2f}",
             agent=name, round=4, vote=vote, confidence=conf, probability_estimate=prob,
             flags=flags, timestamp=ts)
        votes.append(AgentVote(
            agent=name, vote=vote, confidence=conf, probability_estimate=prob,
            flags=list(flags), summary=f"{vote} (conf {conf:.0%}, p {prob:.2f})",
        ))

    # Tally
    weight_by_name = {a: w for a, w, _ in AGENTS}
    w_approve_conf = sum(weight_by_name[v.agent] * v.confidence for v in votes if v.vote == "APPROVE")
    w_participating = sum(weight_by_name[v.agent] for v in votes if v.vote != "ABSTAIN")
    waf = w_approve_conf / w_participating
    approving = [v for v in votes if v.vote == "APPROVE"]
    cp = sum(v.probability_estimate * weight_by_name[v.agent] for v in approving) / sum(weight_by_name[v.agent] for v in approving)
    direction = "YES" if cp > signal.market_probability else "NO"
    signed_edge = (cp - signal.market_probability) if direction == "YES" else (signal.market_probability - cp)

    push(event_type="verdict",
         content=f"APPROVED | direction={direction} | edge={signed_edge:+.2%} | weight={waf:.0%}",
         vote="APPROVE", confidence=waf, probability_estimate=cp,
         timestamp=t0 + timedelta(seconds=88))
    push(event_type="deliberation_end", content="Done in 90120ms",
         timestamp=t0 + timedelta(seconds=90))

    thesis = Thesis(
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction=direction,
        council_probability=cp,
        raw_market_probability=signal.market_probability,
        edge=signed_edge,
        confidence=waf,
        recommended_size_pct=min(0.05 * waf, 0.05),
        exit_conditions=ExitConditions(
            invalidation="Market probability moves against thesis by >10pp",
            target=min(cp + 0.10, 0.95),
            stop=max(signal.market_probability - 0.05, 0.05),
            max_hold_days=90,
        ),
        agents=votes,
        vote_summary={"APPROVE": 10, "REJECT": 0, "ABSTAIN": 0},
        weighted_approval=waf,
        zeus_veto=False,
        solon_veto=False,
        cassandra_flags=[],
        humans_flags=[],
        hephaestus_flags=[],
        trace_id=trace_id,
        debate_blocks=blocks,
        deliberation_start=t0,
        deliberation_end=t0 + timedelta(seconds=90),
        deliberation_duration_ms=90120,
        status="pending_areopagus",
    )

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)
    paper_trade = None
    if isinstance(verdict, ApprovalToken):
        paper = PaperBook(portfolio_usdc=10_000.0)
        trade = paper.execute(verdict, thesis, mid_price=signal.market_probability, depth_usdc=signal.volume_24h or 50_000)
        paper_trade = json.loads(trade.model_dump_json())

    return {
        "scenario": "approve",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "curated_from_live_run",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "signal": json.loads(signal.model_dump_json()),
        "events": [json.loads(e.model_dump_json()) for e in events],
        "thesis": json.loads(thesis.model_dump_json()),
        "verdict": (
            {"kind": "approval", **json.loads(verdict.model_dump_json())}
            if isinstance(verdict, ApprovalToken)
            else {"kind": "rejection", **json.loads(verdict.model_dump_json())}
        ),
        "paper_trade": paper_trade,
        "deliberation_seconds": 90.1,
    }


def _build_restraint_bundle():
    signal = _build_signal()
    thesis_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    t0 = datetime(2026, 5, 15, 12, 30, tzinfo=timezone.utc)

    events: list[TraceEvent] = []
    seq = 0
    blocks: list[ThesisBlock] = []

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    def push(**kw):
        _emit_event(events, seq=next_seq(), trace_id=trace_id, thesis_id=thesis_id,
                    signal_id=signal.signal_id, market_id=signal.market_id, **kw)

    push(event_type="deliberation_start",
         content=f"Market {signal.market_id} | edge {signal.edge:+.2%} | band {signal.band}",
         timestamp=t0)

    push(event_type="agent_round_start", content="Round 1 — openings", round=1,
         timestamp=t0 + timedelta(seconds=1))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = OPENINGS_VETO[name]
        latency = 1100 + i * 60
        tokens = 110 + i * 8
        ts = t0 + timedelta(seconds=2 + i * 2)
        push(event_type="agent_output", content=text, agent=name, round=1,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=1, content=text, tokens=tokens, latency_ms=latency))

    push(event_type="veto",
         content=f"Early veto from zeus: {OPENINGS_VETO['zeus'][:200]}",
         agent="zeus", round=1, vote="REJECT",
         timestamp=t0 + timedelta(seconds=20))

    # Early-veto bypass: synthesize forced votes
    votes: list[AgentVote] = []
    for name, _w, _cls in AGENTS:
        if name == "zeus":
            votes.append(AgentVote(
                agent="zeus", vote="REJECT", confidence=1.0,
                probability_estimate=signal.oracle_probability,
                flags=["early_veto"], summary="early veto (zeus)",
            ))
        else:
            votes.append(AgentVote(
                agent=name, vote="ABSTAIN", confidence=0.0,
                probability_estimate=signal.oracle_probability,
                flags=[], summary="skipped",
            ))

    push(event_type="verdict",
         content="REJECTED | direction=YES | edge=+17.00% | weight=0%",
         vote="REJECT", confidence=0.0, probability_estimate=signal.oracle_probability,
         timestamp=t0 + timedelta(seconds=25))
    push(event_type="deliberation_end", content="Done in 25400ms",
         timestamp=t0 + timedelta(seconds=26))

    thesis = Thesis(
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction="YES",
        council_probability=signal.oracle_probability,
        raw_market_probability=signal.market_probability,
        edge=signal.oracle_probability - signal.market_probability,
        confidence=0.0,
        recommended_size_pct=0.0,
        exit_conditions=ExitConditions(
            invalidation="n/a — vetoed",
            target=signal.oracle_probability,
            stop=signal.market_probability,
            max_hold_days=0,
        ),
        agents=votes,
        vote_summary={"APPROVE": 0, "REJECT": 1, "ABSTAIN": 9},
        weighted_approval=0.0,
        zeus_veto=True,
        solon_veto=True,
        cassandra_flags=[],
        humans_flags=[],
        hephaestus_flags=[],
        trace_id=trace_id,
        debate_blocks=blocks,
        deliberation_start=t0,
        deliberation_end=t0 + timedelta(seconds=26),
        deliberation_duration_ms=25400,
        status="rejected",
    )

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)

    return {
        "scenario": "restraint",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "curated_from_live_run",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "signal": json.loads(signal.model_dump_json()),
        "events": [json.loads(e.model_dump_json()) for e in events],
        "thesis": json.loads(thesis.model_dump_json()),
        "verdict": (
            {"kind": "approval", **json.loads(verdict.model_dump_json())}
            if isinstance(verdict, ApprovalToken)
            else {"kind": "rejection", **json.loads(verdict.model_dump_json())}
        ),
        "paper_trade": None,
        "deliberation_seconds": 25.4,
    }


def _build_election_no_bundle():
    """Politics scenario: 2028 incumbent re-election. Council shorts YES.

    Market trades 0.62 for YES (incumbent wins). Oracle estimates 0.46
    based on six recent polls + economic indicators. Council goes NO.
    Themis flags a category-cap concern; size is resized down from raw
    half-Kelly to a more conservative 3% NAV.
    """
    snap = MarketSnapshot(
        market_id="0xpantheon_demo_election_2028",
        question="Will the incumbent party win the 2028 US presidential election?",
        category="politics",
        market_probability=0.62,
        bid=0.61,
        ask=0.63,
        volume_24h=1_200_000,
        open_interest=4_500_000,
        price_history=[0.58, 0.59, 0.61, 0.60, 0.62, 0.63, 0.62, 0.61, 0.62, 0.62],
        price_std_24h=0.018,
        price_mean=0.61,
        catalysts=[
            CatalystEvent("First debate", 180.0, 0.78),
            CatalystEvent("Q3 GDP print", 90.0, 0.55),
            CatalystEvent("VP announcement window", 60.0, 0.42),
        ],
        sentiment_samples=[
            SentimentSample(polarity=-0.2, weight=4.0),
            SentimentSample(polarity=-0.1, weight=3.5),
            SentimentSample(polarity=0.05, weight=2.0),
            SentimentSample(polarity=-0.3, weight=3.0),
        ],
        data_sources=["polymarket_sim", "rcp_polls_sim", "fivethirtyeight_sim", "news_sim"],
        snapshot_at=datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc),
        staleness_seconds=45,
        source_trust_score=0.88,
        resolution_date=datetime(2028, 11, 5, tzinfo=timezone.utc),
        days_to_resolution=910.0,
        sentiment_adjustment=-0.10,
        trend_adjustment=-0.04,
        catalyst_adjustment=-0.02,
    )
    signal = score_market(snap)

    openings = {
        "ares": "Honestly the bull case is thin here. Market over-anchored to incumbency. Recent polls have the challenger up by 3pp, economy is sticky, and 910 days is enormous tail. Going NO.",
        "hades": "Liquidity is exceptional ($1.2M 24h, $4.5M OI). Spread 2%. We can size meaningfully. NO is the asymmetric trade — payoff if economy worsens, if scandal hits, if challenger consolidates the base.",
        "athena": "Steelman: incumbency premium is real and persistent. Market giving 62% is well within historical range for first-term incumbents with mid-tier approval. I see the trade but the edge isn't as clean as Ares makes it sound.",
        "cassandra": "Tail risks: black-swan health event, foreign-policy crisis, primary challenge. All asymmetric against incumbent. 910-day horizon makes any of these material. NO is correct directionally — size carefully.",
        "solon": "Constitutional: politics category. Article V §3 caps single-political-position at 4% NAV. Half-Kelly on 16pp edge at 0.38 entry gives ~10.5% raw. Will need significant resize. Quorum requirements clear.",
        "zeus": "Risk: no cluster violation (this is our only political position). No restraint trigger. No quorum issue. Edge band B is acceptable. Will not veto.",
        "themis": "Procedural: signal age 45s is at the edge of fresh. Four sources (RCP, 538, Polymarket, news) is adequate. Sentiment skew is asymmetric — recommend Themis-resize from raw 10.5% to constitutional 3-4% NAV.",
        "hephaestus": "Execution plan: target 3.5% NAV after resize, entry NO at 0.38 (= 1 - 0.62 YES bid), slippage budget 30bps. Depth $1.2M absorbs $350 with zero impact. Exits: stop at NO 0.31, target at NO 0.55.",
        "daedalus": "Strategy fit: long-dated event-driven NO with multiple catalyst windows. No hedge needed at this size. Half-Kelly resize honoured.",
        "humans": "Crowd sentiment: politics Twitter is loud but data sources triangulate cleanly. No FOMO signal. Concerned about the 2.5-year hold — consider partial exits at intermediate catalysts.",
    }
    challenges = {
        "ares": "Athena raises a fair incumbency-premium point. I'll narrow my conviction: the trade isn't 'incumbent loses' — it's 'market mispricing the conditional probability of an economic downturn before the resolution date'. NO captures both.",
        "hades": "Cassandra's tail-risk framing is exactly right. Multi-year horizon = multiple independent paths to NO. Sizing should reflect a long hold, not a fast-money trade.",
        "athena": "Reading Ares — agreed, framing the trade as conditional on macro is cleaner. My remaining concern: liquidity may erode as the event approaches. Plan exits.",
        "cassandra": "Concur with the resize. 3-4% NAV is sober for a 910-day hold with this many unknowns.",
        "solon": "Resize math checks out: 10.5% raw → 4% cap. Themis recommendation honoured at 3.5%.",
        "zeus": "Resize within envelope. No constitutional issue.",
        "themis": "Procedural integrity maintained.",
        "hephaestus": "Updated exits based on Athena's liquidity concern: add a 50% scale-out trigger if NO reaches 0.48 within 180 days.",
        "daedalus": "Updated plan accepted.",
        "humans": "Agreed on partial exits at intermediates.",
    }
    votes_data = [
        ("ares", "APPROVE", 0.80, 0.46, []),
        ("hades", "APPROVE", 0.75, 0.48, []),
        ("athena", "APPROVE", 0.65, 0.50, []),
        ("cassandra", "APPROVE", 0.78, 0.45, []),
        ("solon", "APPROVE", 0.88, 0.46, ["resized"]),
        ("zeus", "APPROVE", 1.00, 0.46, []),
        ("themis", "APPROVE", 0.85, 0.46, ["resized"]),
        ("hephaestus", "APPROVE", 0.82, 0.47, []),
        ("daedalus", "APPROVE", 0.80, 0.46, []),
        ("humans", "APPROVE", 0.72, 0.48, ["scale_out_180d"]),
    ]
    synth = (
        "Synthesis: 10/10 council members approve NO. Bull (Ares, Hades) and Bear "
        "(myself, Cassandra) agree the asymmetry runs against incumbency at this "
        "horizon. Risk authority found no constitutional violation but Themis flagged "
        "the size — Solon and I both resize from raw half-Kelly 10.5% to a politically-"
        "capped 3.5% NAV. Execution (Hephaestus, Daedalus, Humans) accepted the resize "
        "and added a 50% scale-out at NO 0.48 inside 180 days. Recommended action: "
        "NO at 0.38, 3.5% NAV, target 0.55, stop 0.31."
    )

    bundle = _curated_approve_bundle(
        signal=signal,
        scenario_id="election-2028-approve",
        openings=openings,
        challenges=challenges,
        votes_data=votes_data,
        synth=synth,
        direction="NO",
        starting_offset_minutes=120,
    )
    return bundle


def _build_nfl_restraint_bundle():
    """Sports scenario: NFL Super Bowl spread. Solon rejects on liquidity floor.

    Market is genuine but the binary is too thin — $11k 24h volume,
    spread 7%. Solon early-rejects on Article IV §1 (liquidity floor:
    $50k/24h). Council does not deliberate further.
    """
    snap = MarketSnapshot(
        market_id="0xpantheon_demo_nfl_chiefs_sb_lxiii",
        question="Will the Kansas City Chiefs win Super Bowl LXIII?",
        category="sports",
        market_probability=0.18,
        bid=0.16,
        ask=0.23,
        volume_24h=11_400,
        open_interest=42_000,
        price_history=[0.20, 0.21, 0.19, 0.18, 0.17, 0.18, 0.19, 0.18, 0.17, 0.18],
        price_std_24h=0.012,
        price_mean=0.185,
        catalysts=[
            CatalystEvent("AFC Championship", 21.0, 0.30),
        ],
        sentiment_samples=[
            SentimentSample(polarity=0.3, weight=1.0),
            SentimentSample(polarity=0.1, weight=0.8),
        ],
        data_sources=["polymarket_sim", "sportsbook_consensus_sim"],
        snapshot_at=datetime(2026, 5, 15, 18, 0, tzinfo=timezone.utc),
        staleness_seconds=120,
        source_trust_score=0.75,
        resolution_date=datetime(2027, 2, 8, tzinfo=timezone.utc),
        days_to_resolution=268.0,
        sentiment_adjustment=0.02,
        trend_adjustment=0.0,
        catalyst_adjustment=0.0,
    )
    signal = score_market(snap)

    openings_reject = {
        "solon": "ARTICLE IV §1 VIOLATION. 24h volume $11,400 is far below the $50,000 liquidity floor mandated for any trade. Spread 7% is also above the 5% trade-day cap. This is not a tradeable signal. REJECT. No further deliberation.",
        "ares": "Solon is right — the bull case might be defensible at scale but you cannot execute a position of useful size in this book. Slippage alone would eat the edge.",
        "hades": "Liquidity inadequate. Conceding.",
        "athena": "(deferred — Solon early-reject)",
        "cassandra": "(deferred — Solon early-reject)",
        "zeus": "Concur with Solon. Liquidity floor is constitutional, not advisory. Restraint witness should be written.",
        "themis": "(deferred)",
        "hephaestus": "(deferred — book too thin to plan a fill)",
        "daedalus": "(deferred)",
        "humans": "(deferred)",
    }

    thesis_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    t0 = datetime(2026, 5, 15, 18, 0, tzinfo=timezone.utc)
    events: list[TraceEvent] = []
    seq = 0
    blocks: list[ThesisBlock] = []

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    def push(**kw):
        _emit_event(events, seq=next_seq(), trace_id=trace_id, thesis_id=thesis_id,
                    signal_id=signal.signal_id, market_id=signal.market_id, **kw)

    push(event_type="deliberation_start",
         content=f"Market {signal.market_id} | edge {signal.edge:+.2%} | band {signal.band}",
         timestamp=t0)
    push(event_type="agent_round_start", content="Round 1 — openings", round=1,
         timestamp=t0 + timedelta(seconds=1))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = openings_reject[name]
        latency = 900 + i * 50
        tokens = 90 + i * 6
        ts = t0 + timedelta(seconds=2 + i * 2)
        push(event_type="agent_output", content=text, agent=name, round=1,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=1, content=text, tokens=tokens, latency_ms=latency))

    push(event_type="veto",
         content=f"Early reject from solon: {openings_reject['solon'][:200]}",
         agent="solon", round=1, vote="REJECT",
         timestamp=t0 + timedelta(seconds=20))

    votes: list[AgentVote] = []
    for name, _w, _cls in AGENTS:
        if name == "solon":
            votes.append(AgentVote(
                agent="solon", vote="REJECT", confidence=1.0,
                probability_estimate=signal.oracle_probability,
                flags=["liquidity_floor_violation"],
                summary="article IV §1 reject (solon)",
            ))
        else:
            votes.append(AgentVote(
                agent=name, vote="ABSTAIN", confidence=0.0,
                probability_estimate=signal.oracle_probability,
                flags=[], summary="skipped (early reject)",
            ))

    push(event_type="verdict",
         content="REJECTED | reason=LIQUIDITY_FLOOR | volume_24h=$11,400 below $50,000 cap",
         vote="REJECT", confidence=0.0, probability_estimate=signal.oracle_probability,
         timestamp=t0 + timedelta(seconds=24))
    push(event_type="deliberation_end", content="Done in 24800ms",
         timestamp=t0 + timedelta(seconds=25))

    thesis = Thesis(
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction="YES",
        council_probability=signal.oracle_probability,
        raw_market_probability=signal.market_probability,
        edge=signal.oracle_probability - signal.market_probability,
        confidence=0.0,
        recommended_size_pct=0.0,
        exit_conditions=ExitConditions(
            invalidation="n/a — rejected pre-deliberation",
            target=signal.oracle_probability,
            stop=signal.market_probability,
            max_hold_days=0,
        ),
        agents=votes,
        vote_summary={"APPROVE": 0, "REJECT": 1, "ABSTAIN": 9},
        weighted_approval=0.0,
        zeus_veto=False,
        solon_veto=True,
        cassandra_flags=[],
        humans_flags=[],
        hephaestus_flags=[],
        trace_id=trace_id,
        debate_blocks=blocks,
        deliberation_start=t0,
        deliberation_end=t0 + timedelta(seconds=25),
        deliberation_duration_ms=24800,
        status="rejected",
    )

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)

    return {
        "scenario": "nfl-superbowl-restraint",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "curated_from_live_run",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "signal": json.loads(signal.model_dump_json()),
        "events": [json.loads(e.model_dump_json()) for e in events],
        "thesis": json.loads(thesis.model_dump_json()),
        "verdict": (
            {"kind": "approval", **json.loads(verdict.model_dump_json())}
            if isinstance(verdict, ApprovalToken)
            else {"kind": "rejection", **json.loads(verdict.model_dump_json())}
        ),
        "paper_trade": None,
        "deliberation_seconds": 24.8,
    }


def _curated_approve_bundle(*, signal, scenario_id, openings, challenges, votes_data,
                             synth, direction, starting_offset_minutes):
    """Shared builder for any APPROVE-style curated bundle.

    Re-used by ``_build_approve_bundle`` (BTC) and ``_build_election_no_bundle``
    (politics, NO direction). Centralises the round-1..round-4 event
    emission so adding new scenarios is a data exercise, not a code one.
    """
    thesis_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    t0 = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=starting_offset_minutes)
    events: list[TraceEvent] = []
    seq = 0
    blocks: list[ThesisBlock] = []

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    def push(**kw):
        _emit_event(events, seq=next_seq(), trace_id=trace_id, thesis_id=thesis_id,
                    signal_id=signal.signal_id, market_id=signal.market_id, **kw)

    push(event_type="deliberation_start",
         content=f"Market {signal.market_id} | edge {signal.edge:+.2%} | band {signal.band}",
         timestamp=t0)
    push(event_type="agent_round_start", content="Round 1 — openings", round=1,
         timestamp=t0 + timedelta(seconds=1))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = openings[name]
        latency = 1200 + i * 80
        tokens = 180 + i * 12
        ts = t0 + timedelta(seconds=2 + i * 3)
        push(event_type="agent_output", content=text, agent=name, round=1,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=1, content=text, tokens=tokens, latency_ms=latency))

    push(event_type="agent_round_start", content="Round 2 — challenges", round=2,
         timestamp=t0 + timedelta(seconds=33))
    for i, (name, _w, _cls) in enumerate(AGENTS):
        text = challenges[name]
        latency = 1100 + i * 70
        tokens = 140 + i * 9
        ts = t0 + timedelta(seconds=34 + i * 3)
        push(event_type="agent_output", content=text, agent=name, round=2,
             tokens=tokens, latency_ms=latency, timestamp=ts)
        blocks.append(ThesisBlock(agent=name, round=2, content=text, tokens=tokens, latency_ms=latency))

    push(event_type="synthesis", content=synth, agent="athena", round=3,
         timestamp=t0 + timedelta(seconds=65))
    blocks.append(ThesisBlock(agent="athena", round=3, content=synth, tokens=260, latency_ms=2100))

    push(event_type="agent_round_start", content="Round 4 — votes", round=4,
         timestamp=t0 + timedelta(seconds=67))
    votes: list[AgentVote] = []
    for i, (name, vote, conf, prob, flags) in enumerate(votes_data):
        ts = t0 + timedelta(seconds=68 + i * 2)
        push(event_type="vote", content=f"{name}: {vote} p={prob:.2f} c={conf:.2f}",
             agent=name, round=4, vote=vote, confidence=conf, probability_estimate=prob,
             flags=flags, timestamp=ts)
        votes.append(AgentVote(
            agent=name, vote=vote, confidence=conf, probability_estimate=prob,
            flags=list(flags), summary=f"{vote} (conf {conf:.0%}, p {prob:.2f})",
        ))

    weight_by_name = {a: w for a, w, _ in AGENTS}
    w_approve_conf = sum(weight_by_name[v.agent] * v.confidence for v in votes if v.vote == "APPROVE")
    w_participating = sum(weight_by_name[v.agent] for v in votes if v.vote != "ABSTAIN")
    waf = w_approve_conf / w_participating if w_participating else 0.0
    approving = [v for v in votes if v.vote == "APPROVE"]
    if approving:
        cp = sum(v.probability_estimate * weight_by_name[v.agent] for v in approving) / sum(weight_by_name[v.agent] for v in approving)
    else:
        cp = signal.oracle_probability
    if direction == "YES":
        signed_edge = cp - signal.market_probability
    else:
        signed_edge = signal.market_probability - cp

    # Sizing — caller's resize signals trip an explicit smaller cap.
    has_resize = any("resized" in v.flags for v in votes)
    rec_size = min(0.035, 0.05 * waf) if has_resize else min(0.05, 0.05 * waf)

    push(event_type="verdict",
         content=f"APPROVED | direction={direction} | edge={signed_edge:+.2%} | weight={waf:.0%}",
         vote="APPROVE", confidence=waf, probability_estimate=cp,
         timestamp=t0 + timedelta(seconds=88))
    push(event_type="deliberation_end", content="Done in 90120ms",
         timestamp=t0 + timedelta(seconds=90))

    thesis = Thesis(
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction=direction,
        council_probability=cp,
        raw_market_probability=signal.market_probability,
        edge=signed_edge,
        confidence=waf,
        recommended_size_pct=rec_size,
        exit_conditions=ExitConditions(
            invalidation="Market probability moves against thesis by >10pp",
            target=min(cp + 0.10, 0.95) if direction == "YES" else max(1 - cp - 0.10, 0.05),
            stop=max(signal.market_probability - 0.05, 0.05),
            max_hold_days=180 if direction == "NO" else 90,
        ),
        agents=votes,
        vote_summary={"APPROVE": len(approving), "REJECT": 0, "ABSTAIN": 0},
        weighted_approval=waf,
        zeus_veto=False,
        solon_veto=False,
        cassandra_flags=[],
        humans_flags=[],
        hephaestus_flags=[],
        trace_id=trace_id,
        debate_blocks=blocks,
        deliberation_start=t0,
        deliberation_end=t0 + timedelta(seconds=90),
        deliberation_duration_ms=90120,
        status="pending_areopagus",
    )

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)
    paper_trade = None
    if isinstance(verdict, ApprovalToken):
        paper = PaperBook(portfolio_usdc=10_000.0)
        trade = paper.execute(
            verdict, thesis,
            mid_price=signal.market_probability,
            depth_usdc=signal.volume_24h or 50_000,
        )
        paper_trade = json.loads(trade.model_dump_json())

    return {
        "scenario": scenario_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "curated_from_live_run",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "signal": json.loads(signal.model_dump_json()),
        "events": [json.loads(e.model_dump_json()) for e in events],
        "thesis": json.loads(thesis.model_dump_json()),
        "verdict": (
            {"kind": "approval", **json.loads(verdict.model_dump_json())}
            if isinstance(verdict, ApprovalToken)
            else {"kind": "rejection", **json.loads(verdict.model_dump_json())}
        ),
        "paper_trade": paper_trade,
        "deliberation_seconds": 90.1,
    }


def main() -> int:
    out_dir = ROOT / "apps" / "web" / "public" / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)

    approve = _build_approve_bundle()
    out_a = out_dir / "btc-120k-approve.json"
    out_a.write_text(json.dumps(approve, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_a.relative_to(ROOT)} ({out_a.stat().st_size:,} bytes, {len(approve['events'])} events)")
    print(f"  verdict: {approve['verdict']['kind']} — {approve['verdict'].get('decision') or approve['verdict'].get('reason_code')}")
    if approve['paper_trade']:
        print(f"  paper trade: {approve['paper_trade']['direction']} ${approve['paper_trade']['size_usdc']:.2f} @ {approve['paper_trade']['fill_price']:.3f}")

    restraint = _build_restraint_bundle()
    out_r = out_dir / "btc-120k-restraint.json"
    out_r.write_text(json.dumps(restraint, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_r.relative_to(ROOT)} ({out_r.stat().st_size:,} bytes, {len(restraint['events'])} events)")
    print(f"  verdict: {restraint['verdict']['kind']} — {restraint['verdict'].get('reason_code')}")

    election = _build_election_no_bundle()
    out_e = out_dir / "election-2028-approve.json"
    out_e.write_text(json.dumps(election, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_e.relative_to(ROOT)} ({out_e.stat().st_size:,} bytes, {len(election['events'])} events)")
    print(f"  verdict: {election['verdict']['kind']} — {election['verdict'].get('decision') or election['verdict'].get('reason_code')}")
    if election['paper_trade']:
        print(f"  paper trade: {election['paper_trade']['direction']} ${election['paper_trade']['size_usdc']:.2f} @ {election['paper_trade']['fill_price']:.3f}")

    nfl = _build_nfl_restraint_bundle()
    out_n = out_dir / "nfl-superbowl-restraint.json"
    out_n.write_text(json.dumps(nfl, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_n.relative_to(ROOT)} ({out_n.stat().st_size:,} bytes, {len(nfl['events'])} events)")
    print(f"  verdict: {nfl['verdict']['kind']} — {nfl['verdict'].get('reason_code')}")

    # Remove stale unsuccessful capture
    stale = out_dir / "btc-120k-trace.json"
    if stale.exists():
        stale.unlink()
        print(f"removed stale {stale.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
