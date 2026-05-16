"""CoinGecko live-price client — async, rate-limited, cached.

Used directly by Apollo / Boule when they need a live crypto reference
(spot price for lead/lag features, historical OHLC for trend / vol).
Independent of the existing ``crypto.py`` DataSource so callers can
mix the two patterns: ``crypto.py`` is for periodic Pythia
publishing, this module is for on-demand reference data.

Free-tier limits:
  - 30 calls / minute / IP
  - No API key required

We respect that with an asyncio min-spacing limiter (≈2s between
calls). Every successful response is cached on disk for
``CACHE_TTL_SECONDS`` so re-asking is free.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger("pythia.coingecko")

BASE_URL = os.environ.get("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
PRO_KEY = os.environ.get("COINGECKO_API_KEY", "").strip()  # demo / pro key
TIMEOUT_SECONDS = float(os.environ.get("COINGECKO_TIMEOUT_S", "12"))
MIN_SPACING_SECONDS = float(os.environ.get("COINGECKO_MIN_SPACING_S", "2.1"))
CACHE_TTL_SECONDS = int(os.environ.get("COINGECKO_CACHE_TTL_S", "60"))
CACHE_DIR = Path(os.environ.get("COINGECKO_CACHE_DIR", ".cache/coingecko"))

SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "MATIC": "matic-network",
    "ARB": "arbitrum",
    "OP": "optimism",
    "AVAX": "avalanche-2",
    "ADA": "cardano",
    "LINK": "chainlink",
    "DOT": "polkadot",
    "USDC": "usd-coin",
    "ATOM": "cosmos",
}


@dataclass(frozen=True)
class SpotPrice:
    symbol: str
    usd: float
    volume_24h_usd: float
    change_24h_pct: float
    updated_at: int  # unix seconds


@dataclass(frozen=True)
class PricePoint:
    timestamp_ms: int
    price_usd: float


@dataclass(frozen=True)
class PriceSeries:
    symbol: str
    days: int
    points: list[PricePoint]

    def closes(self) -> list[float]:
        return [p.price_usd for p in self.points]


class CoinGeckoClient:
    """Async CoinGecko REST client with min-spacing + disk cache."""

    def __init__(self) -> None:
        headers = {"accept": "application/json"}
        if PRO_KEY:
            # Demo + Pro keys ride the same header in v3.
            headers["x-cg-demo-api-key"] = PRO_KEY
            headers["x-cg-pro-api-key"] = PRO_KEY
        self._http = httpx.AsyncClient(timeout=TIMEOUT_SECONDS, headers=headers)
        self._lock = asyncio.Lock()
        self._last_call_t = 0.0

    async def close(self) -> None:
        await self._http.aclose()

    # ── public surface ───────────────────────────────────────────────

    async def spot(self, symbols: list[str]) -> dict[str, SpotPrice]:
        wanted = [s.upper() for s in symbols if s.upper() in SYMBOL_TO_ID]
        if not wanted:
            return {}
        cache_key = "spot::" + ",".join(sorted(wanted))
        cached = _cache_get(cache_key)
        if cached is not None:
            return {s: SpotPrice(**v) for s, v in cached.items()}

        ids = ",".join(SYMBOL_TO_ID[s] for s in wanted)
        payload = await self._get(
            "/simple/price",
            params={
                "ids": ids,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        out: dict[str, SpotPrice] = {}
        for sym in wanted:
            row = payload.get(SYMBOL_TO_ID[sym]) or {}
            usd = row.get("usd")
            if usd is None:
                continue
            out[sym] = SpotPrice(
                symbol=sym,
                usd=float(usd),
                volume_24h_usd=float(row.get("usd_24h_vol") or 0.0),
                change_24h_pct=float(row.get("usd_24h_change") or 0.0),
                updated_at=int(row.get("last_updated_at") or 0),
            )
        _cache_put(cache_key, {s: p.__dict__ for s, p in out.items()}, ttl=CACHE_TTL_SECONDS)
        return out

    async def history(self, symbol: str, days: int = 7) -> Optional[PriceSeries]:
        sym = symbol.upper()
        if sym not in SYMBOL_TO_ID:
            return None
        cache_key = f"history::{sym}::{days}"
        cached = _cache_get(cache_key)
        if cached is not None:
            pts = [PricePoint(**p) for p in cached["points"]]
            return PriceSeries(symbol=sym, days=days, points=pts)
        payload = await self._get(
            f"/coins/{SYMBOL_TO_ID[sym]}/market_chart",
            params={"vs_currency": "usd", "days": days},
        )
        raw = payload.get("prices") or []
        points = [PricePoint(timestamp_ms=int(ts), price_usd=float(p)) for ts, p in raw]
        series = PriceSeries(symbol=sym, days=days, points=points)
        _cache_put(
            cache_key,
            {"points": [p.__dict__ for p in points]},
            ttl=max(CACHE_TTL_SECONDS * 5, 300),  # historical changes slowly
        )
        return series

    # ── plumbing ─────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            retry=retry_if_exception_type(
                (httpx.ConnectError, httpx.ReadTimeout, _TransientError)
            ),
            reraise=True,
        ):
            with attempt:
                await self._enforce_spacing()
                resp = await self._http.get(f"{BASE_URL}{path}", params=params or {})
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise _TransientError(f"coingecko {resp.status_code}: {resp.text[:200]}")
                if resp.status_code >= 400:
                    raise RuntimeError(f"coingecko {resp.status_code}: {resp.text[:300]}")
                return resp.json()
        return {}  # unreachable but satisfies the type checker

    async def _enforce_spacing(self) -> None:
        if MIN_SPACING_SECONDS <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_t
            if elapsed < MIN_SPACING_SECONDS:
                await asyncio.sleep(MIN_SPACING_SECONDS - elapsed)
            self._last_call_t = time.monotonic()


class _TransientError(Exception):
    """Wrap retriable HTTP responses so tenacity backs off."""


# ─── Disk cache ──────────────────────────────────────────────────────


def _cache_key_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


def _cache_get(key: str) -> dict | None:
    p = _cache_key_path(key)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if int(raw.get("expires_at", 0)) < int(time.time()):
            return None
        return raw.get("value")
    except Exception:  # noqa: BLE001
        return None


def _cache_put(key: str, value: dict, ttl: int) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_key_path(key).write_text(
            json.dumps({"value": value, "expires_at": int(time.time()) + ttl}),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        # cache is best-effort
        pass
