"""Tests for the Kalshi venue connector."""

from __future__ import annotations

import json

import pytest

from pythia.kalshi import KalshiSource, map_to_pantheon_market


class _StubResp:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload

    @property
    def text(self) -> str:
        return json.dumps(self._payload)


class _StubClient:
    def __init__(self, mapping: dict[str, _StubResp]):
        self._mapping = mapping
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url: str, *, params: dict | None = None, timeout: float = 10.0):
        self.calls.append((url, params or {}))
        # Match by URL prefix only — params don't matter for routing.
        for key, resp in self._mapping.items():
            if url.endswith(key) or key in url:
                return resp
        raise RuntimeError(f"no stub for {url}")


@pytest.mark.asyncio
async def test_fetch_returns_events():
    client = _StubClient({
        "/events": _StubResp(200, {"events": [{"event_ticker": "BTC-30K"}]}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    snap = await src.fetch()
    assert snap.source == "kalshi"
    assert snap.data["events"][0]["event_ticker"] == "BTC-30K"


@pytest.mark.asyncio
async def test_fetch_markets_for_event():
    client = _StubClient({
        "/markets": _StubResp(200, {"markets": [{"ticker": "BTC-30K-Y"}]}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    markets = await src.fetch_markets_for_event("BTC-30K")
    assert markets[0]["ticker"] == "BTC-30K-Y"


@pytest.mark.asyncio
async def test_fetch_market():
    client = _StubClient({
        "/markets/BTC-30K-Y": _StubResp(200, {"market": {"ticker": "BTC-30K-Y", "yes_bid": 35, "yes_ask": 38}}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    m = await src.fetch_market("BTC-30K-Y")
    assert m["yes_bid"] == 35


@pytest.mark.asyncio
async def test_fetch_mid_price_normalises_cents_to_unit():
    client = _StubClient({
        "/markets/BTC-30K-Y": _StubResp(200, {"market": {"yes_bid": 40, "yes_ask": 60}}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    mid = await src.fetch_mid_price("BTC-30K-Y")
    assert mid == pytest.approx(0.50, abs=1e-9)


@pytest.mark.asyncio
async def test_fetch_mid_price_clamps_to_unit():
    client = _StubClient({
        "/markets/X": _StubResp(200, {"market": {"yes_bid": -10, "yes_ask": 200}}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    mid = await src.fetch_mid_price("X")
    assert 0.0 <= mid <= 1.0


@pytest.mark.asyncio
async def test_fetch_orderbook_default_when_missing():
    client = _StubClient({
        "/markets/X/orderbook": _StubResp(200, {}),
    })
    src = KalshiSource(client=client)  # type: ignore[arg-type]
    book = await src.fetch_orderbook("X")
    assert book == {"yes": [], "no": []}


def test_map_to_pantheon_market_normalises_to_unit():
    raw = {
        "ticker": "BTC-30K",
        "title": "Will BTC hit 30k?",
        "category": "crypto",
        "yes_bid": 35,
        "yes_ask": 38,
        "volume": 1234.0,
        "open_interest": 999.0,
        "close_time": "2026-12-31T23:59:59Z",
        "status": "open",
    }
    m = map_to_pantheon_market(raw)
    assert m["venue"] == "kalshi"
    assert m["market_id"] == "BTC-30K"
    assert m["yes_bid"] == pytest.approx(0.35)
    assert m["yes_ask"] == pytest.approx(0.38)
    assert m["yes_mid"] == pytest.approx(0.365)


def test_map_handles_missing_fields():
    m = map_to_pantheon_market({})
    assert m["yes_bid"] == 0.0
    assert m["yes_ask"] == 1.0
    assert m["yes_mid"] == 0.5
    assert m["category"] == "other"
