"""Run a single end-to-end Pantheon deliberation against a live LLM.

  1. Loads .env (PRIVATE_KEY, GEMINI_API_KEY or ANTHROPIC_API_KEY).
  2. Picks the LLM provider from BOULE_LLM_PROVIDER (defaults to anthropic;
     pass --provider gemini to override).
  3. Hits the live Polymarket CLOB, picks the first market that clears
     Apollo's prefilter, scores it into a Signal.
  4. Connects to the local Redis container.
  5. Runs the full 4-round Boule deliberation against the real LLM,
     publishing trace events to ``boule:traces`` as it goes.
  6. Pushes the resulting Thesis through Areopagus with a clean
     PortfolioState; on APPROVE/RESIZE, executes a paper trade; on
     REJECT, prints the reason code.

No funds touched. No Polymarket orders submitted. Real LLM only.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import httpx
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
    """Load .env into os.environ, OVERRIDING any pre-existing shell values.

    Important: the shell may carry stale keys from earlier sessions; .env
    is the source of truth for this process.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


async def _pick_market(http: httpx.AsyncClient) -> dict | None:
    """Pull a batch of Polymarket markets and pick the first one Apollo
    will actually score (prefilter passes).

    Falls back to ``None`` if Polymarket is unreachable from this network
    (it is geo-blocked in several countries). The caller then uses a
    synthetic-but-realistic snapshot so the LLM still runs.
    """
    from apollo.filters import prefilter
    from apollo.sources.polymarket import snapshot_from_market_payload

    try:
        resp = await http.get(
            "https://clob.polymarket.com/markets",
            params={"limit": 200},
            timeout=20.0,
        )
        resp.raise_for_status()
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError):
        return None
    payload = resp.json()
    markets = payload.get("data") if isinstance(payload, dict) else payload
    for market in markets or []:
        try:
            snap = snapshot_from_market_payload(market)
        except Exception:
            continue
        if prefilter(snap).passed:
            return market
    return None


def _synthetic_signal():
    """Realistic Polymarket-shaped MarketSnapshot for offline demos."""
    from datetime import datetime, timedelta, timezone

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
        days_to_resolution=(datetime(2026, 12, 31, tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 86_400,
        sentiment_adjustment=0.08,
        trend_adjustment=0.05,
        catalyst_adjustment=0.04,
    )
    return score_market(snap), snap.question


async def main() -> int:
    parser = argparse.ArgumentParser(prog="demo_live_council")
    parser.add_argument("--provider", choices=("gemini", "anthropic"), default=None)
    parser.add_argument("--portfolio", type=float, default=10_000.0)
    args = parser.parse_args()

    _load_env(ROOT / ".env")
    if args.provider:
        os.environ["BOULE_LLM_PROVIDER"] = args.provider

    provider = os.environ.get("BOULE_LLM_PROVIDER", "anthropic")
    print(f"=== live council demo (provider={provider}) ===")

    from apollo.scorer import score_market
    from apollo.sources.polymarket import snapshot_from_market_payload
    from areopagus.court import AreopagusCourt
    from areopagus.gates import PortfolioState
    from pantheon_core.schema import ApprovalToken, RejectionRecord
    from strategos.paper import PaperBook

    from boule.swarm import deliberate

    redis = await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )

    async with httpx.AsyncClient() as http:
        market = await _pick_market(http)
    if market is None:
        print("Polymarket unreachable (geo-block or rate limit) — using synthetic signal")
        signal, _ = _synthetic_signal()
    else:
        snap = snapshot_from_market_payload(market)
        signal = score_market(snap)
    print(f"\nsignal:")
    print(f"  market_id   = {signal.market_id}")
    print(f"  question    = {signal.question[:90]}")
    print(f"  category    = {signal.category}")
    print(f"  market p    = {signal.market_probability:.2%}")
    print(f"  oracle p    = {signal.oracle_probability:.2%}")
    print(f"  edge        = {signal.edge:+.2%}")
    print(f"  band        = {signal.band} (score {signal.band_score:.3f})")
    print(f"  liquidity   = {signal.liquidity_score:.3f}")
    print(f"  spread      = {signal.spread:.2%}")
    print(f"  staleness   = {signal.staleness_seconds}s")

    print(f"\nbeginning {provider} deliberation...")
    t0 = time.perf_counter()
    thesis = await deliberate(signal, redis_client=redis)
    elapsed = time.perf_counter() - t0
    print(f"\nthesis (deliberation {elapsed:.1f}s):")
    print(f"  status              = {thesis.status}")
    print(f"  direction           = {thesis.direction}")
    print(f"  council p           = {thesis.council_probability:.2%}")
    print(f"  weighted approval   = {thesis.weighted_approval:.2%}")
    print(f"  confidence          = {thesis.confidence:.2%}")
    print(f"  recommended size    = {thesis.recommended_size_pct:.2%}")
    print(f"  zeus_veto           = {thesis.zeus_veto}")
    print(f"  solon_veto          = {thesis.solon_veto}")
    print(f"  cassandra_flags     = {thesis.cassandra_flags}")
    print(f"  votes               = {thesis.vote_summary}")
    print(f"  per-agent:")
    for v in thesis.agents:
        print(f"    {v.agent:11s} {v.vote:8s} c={v.confidence:.2f} p={v.probability_estimate:.2f}  flags={v.flags}")

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)
    print(f"\nareopagus verdict:")
    if isinstance(verdict, ApprovalToken):
        print(f"  decision       = {verdict.decision}")
        print(f"  final size     = {verdict.final_size_pct:.2%}")
        print(f"  kelly fraction = {verdict.kelly_fraction:.3f}")
        print(f"  note           = {verdict.note}")
        paper = PaperBook(portfolio_usdc=args.portfolio)
        trade = paper.execute(verdict, thesis, mid_price=signal.market_probability, depth_usdc=signal.volume_24h or 50_000)
        print(f"\npaper trade:")
        print(f"  direction   = {trade.direction}")
        print(f"  size_usdc   = ${trade.size_usdc:,.2f}")
        print(f"  entry price = {trade.entry_price:.3f}")
        print(f"  fill price  = {trade.fill_price:.3f}")
        print(f"  status      = {trade.status}")
    else:
        assert isinstance(verdict, RejectionRecord)
        print(f"  REJECTED: {verdict.reason_code}")
        print(f"  note: {verdict.note}")
        print("\n>>> this is a Proof of Restraint candidate <<<")
        print("    Areopagus would write this to the on-chain ProofOfRestraint contract.")

    await redis.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
