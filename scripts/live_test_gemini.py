"""Live council deliberation against Gemini, timing every call.

Records a structured JSON artifact under ``artifacts/live_test_<UTC>.json``
with per-agent / per-round timings, token counts, model fingerprint,
and an estimated USD cost based on Gemini 2.5 Flash Lite paid-tier
pricing ($0.10 / MTok in, $0.40 / MTok out as of 2026-05).

Designed to run WITHOUT Redis / Postgres / IPFS — pure Gemini API
calls plus the agent prompt loader. Useful as:

  - Smoke test for a fresh ``GEMINI_API_KEY`` install
  - End-to-end timing baseline before / after a perf change
  - Demo fodder that produces a reproducible artifact

Usage:
    uv run --project services/boule python scripts/live_test_gemini.py
or, if running outside uv:
    python -m pip install httpx tenacity structlog
    GEMINI_API_KEY=... python scripts/live_test_gemini.py

Override model via BOULE_GEMINI_MODEL=gemini-2.5-flash (or pro).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
PROMPTS = ROOT / "services" / "boule" / "src" / "boule" / "prompts"


# ─── env loading ─────────────────────────────────────────────────────


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        out[k] = v
    return out


def ensure_env() -> None:
    env = load_dotenv(ROOT / ".env")
    # .env is authoritative for this script — overwrite shell-inherited
    # values. A stale GEMINI_API_KEY in the user's shell environment is
    # the most common reason this script silently failed with
    # API_KEY_INVALID errors after .env was updated.
    for k, v in env.items():
        if v:
            os.environ[k] = v
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY missing — populate .env or export it before running.")


# ─── Gemini call ─────────────────────────────────────────────────────


MODEL = os.environ.get("BOULE_GEMINI_MODEL", "gemini-2.5-flash-lite")
# Free tier of gemini-2.5-flash-lite caps at 10 RPM = 6s spacing min.
# Paid Tier 1 lifts this to 1000+ RPM. Default to safe free-tier spacing
# and let LIVE_TEST_SPACING_S override when running on paid quota.
SPACING_S = float(os.environ.get("LIVE_TEST_SPACING_S", "6.2"))
MAX_TOKENS = int(os.environ.get("LIVE_TEST_MAX_TOKENS", "320"))
# Retry-on-429 with the upstream retry_after suggestion, capped.
RETRY_429_MAX_S = float(os.environ.get("LIVE_TEST_RETRY_429_MAX_S", "20"))
PRICE_IN = float(os.environ.get("LIVE_TEST_PRICE_IN_USD_PER_MTOK", "0.10"))
PRICE_OUT = float(os.environ.get("LIVE_TEST_PRICE_OUT_USD_PER_MTOK", "0.40"))


async def gemini_call(system: str, user: str) -> dict:
    """One blocking Gemini request. Returns the full call record.

    Includes a single retry on HTTP 429 using the upstream
    ``retry_after`` suggestion (capped at LIVE_TEST_RETRY_429_MAX_S).
    """
    import httpx

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={os.environ['GEMINI_API_KEY']}"
    )
    payload = {
        # v1beta uses camelCase `systemInstruction`; the snake_case
        # alias returns API_KEY_INVALID on some endpoints, which is
        # misleading — the failure is actually payload validation.
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": MAX_TOKENS, "temperature": 0.7},
    }

    retried = 0
    t_overall = time.perf_counter()
    while True:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(url, json=payload)
        if resp.status_code != 429 or retried >= 1:
            break
        wait_s = _parse_retry_after(resp.text)
        wait_s = min(max(1.0, wait_s), RETRY_429_MAX_S)
        print(f"      429 — backing off {wait_s:.1f}s and retrying once", flush=True)
        await asyncio.sleep(wait_s)
        retried += 1

    duration_ms = int((time.perf_counter() - t_overall) * 1000)
    record: dict = {
        "duration_ms": duration_ms,
        "http_status": resp.status_code,
        "retried_429": retried,
    }
    if resp.status_code != 200:
        record["error"] = resp.text[:600]
        return record

    body = resp.json()
    candidates = body.get("candidates") or []
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
    usage = body.get("usageMetadata") or {}
    tokens_in = int(usage.get("promptTokenCount", 0))
    tokens_out = int(usage.get("candidatesTokenCount", 0))
    record.update({
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "model_version": body.get("modelVersion") or MODEL,
        "preview": text[:240],
        "finish_reason": (candidates[0].get("finishReason") if candidates else None),
    })
    return record


def _parse_retry_after(body: str) -> float:
    """Pull the seconds value out of the 429 body's `Please retry in Xs.`"""
    import re

    m = re.search(r"retry in ([0-9.]+)s", body)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return 5.0


# ─── orchestration ───────────────────────────────────────────────────


SIGNAL = {
    "market_id": "0xPM-BTC-120K-2026-12-31",
    "question": "Will Bitcoin trade above $120,000 on or before 2026-12-31 UTC?",
    "category": "crypto",
    "market_probability": 0.42,
    "oracle_probability": 0.58,
    "edge_signed": 0.16,
    "band": "A",
    "liquidity_score": 0.82,
    "volatility_score": 0.55,
    "catalyst_score": 0.71,
    "sentiment_score": 0.61,
    "days_to_resolution": 230.0,
    "volume_24h": 412_300.0,
    "open_interest": 1_870_000.0,
}


def signal_context() -> str:
    s = SIGNAL
    return (
        f"Market: {s['question']}\n"
        f"Market ID: {s['market_id']}\n"
        f"Category: {s['category']}\n"
        f"Market probability (YES): {s['market_probability']:.2%}\n"
        f"Oracle probability (YES): {s['oracle_probability']:.2%}\n"
        f"Signed edge: {s['edge_signed']:+.2%}\n"
        f"Band: {s['band']} | liq {s['liquidity_score']:.2f} | "
        f"vol {s['volatility_score']:.2f} | cat {s['catalyst_score']:.2f}\n"
        f"Days to resolution: {s['days_to_resolution']:.0f}\n"
        f"Volume 24h: ${s['volume_24h']:,.0f} | OI: ${s['open_interest']:,.0f}\n"
    )


# Lean roster — pick the agents we actually have prompts for in this repo.
# Override via LIVE_TEST_ROSTER="ares,athena,hades,cassandra,zeus,eris".
DEFAULT_ROSTER = [
    "ares",        # bull thesis
    "athena",      # synthesis / logical consistency
    "hades",       # bear thesis
    "cassandra",   # tail risk
    "zeus",        # constitutional veto
    "solon",       # compliance veto
    "themis",      # risk arbiter
    "hephaestus",  # craft / execution prep
    "humans",      # human-in-the-loop input
    "eris",        # adversarial dissent (Tier C)
]
AGENT_ROSTER = (
    [s.strip() for s in os.environ["LIVE_TEST_ROSTER"].split(",") if s.strip()]
    if os.environ.get("LIVE_TEST_ROSTER")
    else DEFAULT_ROSTER
)


ROUND_INSTRUCTIONS = {
    1: (
        "Round 1 opening (≤ 180 tokens). Stay in character. Give a clear "
        "first-pass take on this signal — is the edge real and tradable?"
    ),
    4: (
        "Round 4 vote. Reply EXACTLY in this format:\n"
        "VOTE: APPROVE|REJECT|ABSTAIN\n"
        "CONFIDENCE: 0.XX\n"
        "PROBABILITY: 0.XX\n"
        "FLAGS: NONE | <comma list>\n"
        "REASON: one sentence."
    ),
}


def load_prompt(name: str) -> str:
    p = PROMPTS / f"{name}.md"
    if not p.exists():
        return f"You are {name}, a Pantheon Trades council agent. Reply concisely, in character."
    return p.read_text(encoding="utf-8")


async def run(roster: list[str]) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    t_start = time.perf_counter()
    rounds_out: list[dict] = []

    for round_num in (1, 4):
        agents_out = []
        for agent in roster:
            system = load_prompt(agent)
            user = (
                f"{signal_context()}\n\n"
                f"{ROUND_INSTRUCTIONS[round_num]}"
            )
            print(f"  [round {round_num}] {agent} -> calling gemini ...", flush=True)
            rec = await gemini_call(system, user)
            rec["agent"] = agent
            agents_out.append(rec)
            await asyncio.sleep(SPACING_S)
        rounds_out.append({"round": round_num, "agents": agents_out})

    t_end = time.perf_counter()
    total_ms = int((t_end - t_start) * 1000)

    # Aggregate.
    total_in = sum(a.get("tokens_in", 0) for r in rounds_out for a in r["agents"])
    total_out = sum(a.get("tokens_out", 0) for r in rounds_out for a in r["agents"])
    cost_usd = (total_in / 1_000_000) * PRICE_IN + (total_out / 1_000_000) * PRICE_OUT
    failures = [
        a for r in rounds_out for a in r["agents"] if a.get("http_status") != 200
    ]
    return {
        "schema": "pantheon-live-test-v1",
        "model": MODEL,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_ms": total_ms,
        "spacing_seconds_between_calls": SPACING_S,
        "signal": SIGNAL,
        "rounds": rounds_out,
        "tokens": {"in": total_in, "out": total_out},
        "cost_usd_estimate": round(cost_usd, 6),
        "pricing_assumed": {"input_per_mtok": PRICE_IN, "output_per_mtok": PRICE_OUT},
        "failure_count": len(failures),
        "agent_count": len(roster),
    }


# ─── entrypoint ──────────────────────────────────────────────────────


def main() -> None:
    ensure_env()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS / f"live_test_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"

    print(f"model: {MODEL}")
    print(f"spacing: {SPACING_S}s between calls")
    print(f"writing artifact to: {out_path}")
    print()

    result = asyncio.run(run(AGENT_ROSTER))

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nDone. Artifact: {out_path}")
    print(
        f"calls: {result['agent_count'] * 2} | "
        f"failures: {result['failure_count']} | "
        f"total: {result['total_duration_ms']} ms | "
        f"cost: ${result['cost_usd_estimate']:.6f}"
    )


if __name__ == "__main__":
    main()
