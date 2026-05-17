"""Capture a real Gemini council deliberation as a static JSON bundle.

Output: apps/web/public/demo/btc-120k-trace.json

The file is the exact shape consumed by the /demo replay viewer. Run
this offline whenever the demo trace gets stale.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import redis.asyncio as aioredis

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "boule" / "src",
    ROOT / "services" / "areopagus" / "src",
    ROOT / "services" / "strategos" / "src",
):
    sys.path.insert(0, str(p))


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


def _synthetic_signal():
    from apollo.features.catalyst import CatalystEvent
    from apollo.features.sentiment import SentimentSample
    from apollo.scorer import MarketSnapshot, score_market

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
        snapshot_at=datetime.now(timezone.utc),
        staleness_seconds=20,
        source_trust_score=0.92,
        resolution_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
        days_to_resolution=(
            datetime(2026, 12, 31, tzinfo=timezone.utc) - datetime.now(timezone.utc)
        ).total_seconds()
        / 86_400,
        sentiment_adjustment=0.08,
        trend_adjustment=0.05,
        catalyst_adjustment=0.04,
    )
    return score_market(snap), snap


async def main() -> int:
    _load_env(ROOT / ".env")
    os.environ["BOULE_LLM_PROVIDER"] = "gemini"
    os.environ.setdefault("BOULE_GEMINI_CONCURRENCY", "1")

    from areopagus.court import AreopagusCourt
    from areopagus.gates import PortfolioState
    from pantheon_core.schema import ApprovalToken
    from strategos.paper import PaperBook

    from boule.swarm import deliberate

    redis = await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )

    signal, snap = _synthetic_signal()
    print(f"signal: {signal.market_id} edge={signal.edge:+.2%}")

    # Patch the Tracer to capture events in-process — we still emit to Redis
    # but we also need the raw list to serialize.
    from boule import trace as trace_mod

    captured: list = []
    real_emit = trace_mod.Tracer.emit

    async def capturing_emit(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        ev = await real_emit(self, *args, **kwargs)
        captured.append(ev)
        return ev

    trace_mod.Tracer.emit = capturing_emit  # type: ignore[assignment]

    print("deliberating...")
    t0 = time.perf_counter()
    thesis = await deliberate(signal, redis_client=redis)
    elapsed = time.perf_counter() - t0
    print(f"thesis: status={thesis.status} approval={thesis.weighted_approval:.0%} ({elapsed:.1f}s)")

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)

    paper_trade = None
    if isinstance(verdict, ApprovalToken):
        paper = PaperBook(portfolio_usdc=10_000.0)
        trade = paper.execute(
            verdict,
            thesis,
            mid_price=signal.market_probability,
            depth_usdc=signal.volume_24h or 50_000,
        )
        paper_trade = json.loads(trade.model_dump_json())

    bundle = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "provider": os.environ.get("BOULE_LLM_PROVIDER", "gemini"),
        "model": os.environ.get("BOULE_GEMINI_MODEL", "gemini-2.5-flash"),
        "signal": json.loads(signal.model_dump_json()),
        "events": [json.loads(e.model_dump_json()) for e in captured],
        "thesis": json.loads(thesis.model_dump_json()),
        "verdict": (
            {"kind": "approval", **json.loads(verdict.model_dump_json())}
            if isinstance(verdict, ApprovalToken)
            else {"kind": "rejection", **json.loads(verdict.model_dump_json())}
        ),
        "paper_trade": paper_trade,
        "deliberation_seconds": elapsed,
    }

    out = ROOT / "apps" / "web" / "public" / "demo" / "btc-120k-trace.json"
    out.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes, {len(captured)} events)")

    await redis.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
