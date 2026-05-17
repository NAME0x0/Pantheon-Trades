"""Backtest harness — replay Boule council against resolved Polymarket markets.

This is the alpha-proving skeleton. Running it for real takes meaningful
LLM API budget (~$3-15 / hundred markets depending on provider). The
output is per-market Brier scores per agent which Ostrakon-equivalent
calibration can then use to tune weights.

Pipeline:

  1. Fetch resolved markets from Polymarket (CLOB markets-history) or
     fall back to a local JSONL cache.
  2. For each market:
       - Reconstruct an Apollo-shaped Signal as of `--lookback-days`
         before resolution. Use stored historical price/volume rather
         than live values.
       - Strip resolution from the Signal (we must not leak the answer).
       - Run Boule.deliberate against the chosen provider. The LLM
         cache (services/boule/.../llm/cache.py) means a second run
         re-uses the first run's deliberation entirely free.
       - Compare council probability to realised outcome (1 = YES, 0 = NO).
  3. Emit a CSV with per-market and per-agent Brier scores.

Counters:

  * Brier per market   = (predicted_p - actual)^2
  * Brier per agent    = mean over markets the agent voted on
  * Calibration buckets: 10% width, count predicted vs actual

Treat the CSV as the input to a Platt / isotonic calibration; that step
lives in Ostrakon (services/ostrakon) and is intentionally separate so
this script stays a pure data-collection tool.

Usage:

    uv run python tests/backtest_polymarket.py \\
        --provider gemini \\
        --limit 25 \\
        --lookback-days 14 \\
        --out backtest_results.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import httpx

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "boule" / "src",
    ROOT / "services" / "areopagus" / "src",
):
    sys.path.insert(0, str(p))


# ──────────────────────────────────────────────────────────────────────
# Polymarket data fetch — happy path is CLOB markets-history. Behind a
# geo-block (Polymarket is restricted in many regions) we fall back to
# a JSONL cache the user can populate from any third-party mirror.
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResolvedMarket:
    market_id: str
    question: str
    category: str
    outcome_yes: bool           # True if YES resolved, False if NO
    resolved_at: datetime
    pre_resolution_probability: float
    pre_resolution_volume: float


CACHE_FILE = ROOT / ".cache" / "polymarket_resolved.jsonl"


async def fetch_resolved_markets(limit: int) -> list[ResolvedMarket]:
    """Try Polymarket CLOB; fall back to local cache."""
    try:
        return await _fetch_polymarket_clob(limit)
    except Exception as e:  # noqa: BLE001
        print(f"[backtest] CLOB fetch failed ({e}); using cache at {CACHE_FILE}")
        return _load_cache(limit)


async def _fetch_polymarket_clob(limit: int) -> list[ResolvedMarket]:
    """Pull resolved markets from Polymarket's CLOB."""
    url = "https://clob.polymarket.com/markets-history"
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.get(url, params={"limit": limit, "status": "resolved"})
        r.raise_for_status()
        payload = r.json()
    items = payload.get("data") or payload if isinstance(payload, list) else []
    out: list[ResolvedMarket] = []
    for m in items[:limit]:
        try:
            out.append(_parse_clob_market(m))
        except Exception:  # noqa: BLE001
            continue
    return out


def _parse_clob_market(m: dict) -> ResolvedMarket:
    resolved_at = datetime.fromisoformat(
        (m.get("end_date") or m.get("resolved_at") or "").replace("Z", "+00:00")
    )
    return ResolvedMarket(
        market_id=str(m.get("condition_id") or m.get("market_id") or m.get("id")),
        question=str(m.get("question") or ""),
        category=str(m.get("category") or "other"),
        outcome_yes=bool(m.get("outcome_yes") or m.get("yes_won") or False),
        resolved_at=resolved_at,
        pre_resolution_probability=float(m.get("pre_resolution_p", 0.5)),
        pre_resolution_volume=float(m.get("volume_24h", 0.0)),
    )


def _load_cache(limit: int) -> list[ResolvedMarket]:
    if not CACHE_FILE.exists():
        return []
    out: list[ResolvedMarket] = []
    with CACHE_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
                out.append(_parse_clob_market(m))
            except Exception:  # noqa: BLE001
                continue
            if len(out) >= limit:
                break
    return out


# ──────────────────────────────────────────────────────────────────────
# Signal reconstruction — strip the outcome before handing to Apollo.
# ──────────────────────────────────────────────────────────────────────


def _signal_for(market: ResolvedMarket, lookback_days: int):
    """Build a synthetic Apollo Signal as of (resolved_at - lookback).

    For a proper backtest you would substitute real historical price /
    volume here. The skeleton uses pre_resolution_probability + a flat
    feature envelope so the script runs end-to-end out of the box.
    """
    from apollo.scorer import MarketSnapshot, score_market

    snap = MarketSnapshot(
        market_id=market.market_id,
        question=market.question,
        category=market.category or "other",
        market_probability=market.pre_resolution_probability,
        bid=max(market.pre_resolution_probability - 0.01, 0.01),
        ask=min(market.pre_resolution_probability + 0.01, 0.99),
        volume_24h=market.pre_resolution_volume or 50_000,
        open_interest=market.pre_resolution_volume or 100_000,
        price_history=[market.pre_resolution_probability] * 10,
        price_std_24h=0.04,
        price_mean=market.pre_resolution_probability,
        catalysts=[],
        sentiment_samples=[],
        data_sources=["backtest"],
        snapshot_at=market.resolved_at - timedelta(days=lookback_days),
        staleness_seconds=60,
        source_trust_score=0.8,
        resolution_date=market.resolved_at,
        days_to_resolution=lookback_days,
        sentiment_adjustment=0.0,
        trend_adjustment=0.0,
        catalyst_adjustment=0.0,
    )
    return score_market(snap)


# ──────────────────────────────────────────────────────────────────────
# Per-market deliberation + Brier scoring
# ──────────────────────────────────────────────────────────────────────


async def _run_one(market: ResolvedMarket, lookback_days: int) -> dict:
    from boule.swarm import deliberate
    import redis.asyncio as aioredis

    redis = await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    try:
        signal = _signal_for(market, lookback_days)
        thesis = await deliberate(signal, redis_client=redis)
    finally:
        await redis.aclose()

    actual = 1.0 if market.outcome_yes else 0.0
    pred = float(thesis.council_probability)
    brier = (pred - actual) ** 2

    per_agent: list[dict] = []
    for v in thesis.agents:
        agent_pred = float(v.probability_estimate)
        per_agent.append(
            {
                "agent": v.agent,
                "vote": v.vote,
                "probability_estimate": agent_pred,
                "confidence": float(v.confidence),
                "brier": (agent_pred - actual) ** 2,
            }
        )

    return {
        "market_id": market.market_id,
        "question": market.question[:120],
        "actual": actual,
        "council_probability": pred,
        "brier": brier,
        "weighted_approval": float(thesis.weighted_approval),
        "status": thesis.status,
        "zeus_veto": thesis.zeus_veto,
        "solon_veto": thesis.solon_veto,
        "per_agent": per_agent,
    }


# ──────────────────────────────────────────────────────────────────────
# CSV writer
# ──────────────────────────────────────────────────────────────────────


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        path.write_text("market_id,question,actual,council_probability,brier\n", encoding="utf-8")
        return
    fieldnames = [
        "market_id",
        "question",
        "actual",
        "council_probability",
        "brier",
        "weighted_approval",
        "status",
        "zeus_veto",
        "solon_veto",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _per_agent_csv(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flat: list[dict] = []
    for r in rows:
        for a in r.get("per_agent", []):
            flat.append(
                {
                    "market_id": r["market_id"],
                    **a,
                }
            )
    if not flat:
        path.write_text("market_id,agent,vote,probability_estimate,confidence,brier\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["market_id", "agent", "vote", "probability_estimate", "confidence", "brier"],
        )
        w.writeheader()
        w.writerows(flat)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────


async def main() -> int:
    parser = argparse.ArgumentParser(prog="backtest_polymarket")
    parser.add_argument("--provider", choices=("gemini", "anthropic", "openai", "openrouter", "groq", "deepseek", "xai", "ollama", "lm_studio"), default=None)
    parser.add_argument("--limit", type=int, default=10, help="markets to replay")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--out", type=Path, default=Path("backtest_results.csv"))
    parser.add_argument("--out-agents", type=Path, default=Path("backtest_per_agent.csv"))
    args = parser.parse_args()

    # Load env
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

    if args.provider:
        os.environ["BOULE_LLM_PROVIDER"] = args.provider
    print(f"=== Polymarket backtest (provider={os.environ.get('BOULE_LLM_PROVIDER', 'anthropic')}) ===")

    markets = await fetch_resolved_markets(args.limit)
    if not markets:
        print("[backtest] no markets to replay; populate .cache/polymarket_resolved.jsonl or unblock CLOB")
        return 1
    print(f"[backtest] replaying {len(markets)} market(s) at lookback={args.lookback_days}d")

    results: list[dict] = []
    for i, m in enumerate(markets, start=1):
        print(f"  ({i}/{len(markets)}) {m.market_id[:32]}  {m.question[:80]}")
        try:
            r = await _run_one(m, args.lookback_days)
            results.append(r)
            print(
                f"    council_p={r['council_probability']:.3f} actual={r['actual']:.0f} brier={r['brier']:.4f}"
            )
        except Exception as e:  # noqa: BLE001
            print(f"    [skip] {e}")

    _write_csv(args.out, results)
    _per_agent_csv(args.out_agents, results)

    if results:
        avg_brier = sum(r["brier"] for r in results) / len(results)
        print(f"\n[backtest] mean Brier across {len(results)} markets = {avg_brier:.4f}")
        print("  Brier 0.250 = coin flip · 0.000 = perfect")
        print(f"  out: {args.out}")
        print(f"  out: {args.out_agents}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
