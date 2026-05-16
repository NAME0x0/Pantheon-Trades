"""Tests for the Polymarket L2 WS client.

We do not hit the network. The client exposes ``inject_for_testing``
plus a synchronous ``_parse_levels`` helper that lets us exercise the
delta-handling path without standing up a fake websocket server.
"""

from __future__ import annotations

import asyncio

import pytest

from pythia.polymarket_ws import (
    OrderBookLevel,
    OrderBookSnapshot,
    PolymarketL2Client,
    _parse_levels,
)


def test_parse_levels_handles_dict_form():
    raw = [{"price": "0.42", "size": "1000"}, {"price": "0.41", "size": "500"}]
    out = _parse_levels(raw)
    assert len(out) == 2
    assert out[0].price == pytest.approx(0.42)
    assert out[0].size_usdc == pytest.approx(1000.0)


def test_parse_levels_handles_pair_form():
    raw = [(0.42, 1000), (0.41, 500)]
    out = _parse_levels(raw)
    assert len(out) == 2


def test_parse_levels_skips_zero_size():
    raw = [{"price": "0.42", "size": "0"}, {"price": "0.41", "size": "10"}]
    out = _parse_levels(raw)
    assert len(out) == 1
    assert out[0].price == pytest.approx(0.41)


def test_parse_levels_skips_out_of_range_prices():
    """Polymarket prices are bounded to [0, 1]; reject obvious garbage."""
    raw = [{"price": "1.5", "size": "100"}, {"price": "-0.1", "size": "10"}, {"price": "0.5", "size": "5"}]
    out = _parse_levels(raw)
    assert len(out) == 1
    assert out[0].price == pytest.approx(0.5)


def test_parse_levels_resilient_to_garbage():
    raw = [{"price": "junk", "size": "10"}, None, [], {"price": "0.42"}]
    out = _parse_levels(raw)
    # None of these should make it through; size missing/0 too.
    assert out == []


def test_inject_for_testing_round_trip():
    client = PolymarketL2Client(market_ids=["m1", "m2"])
    snap = OrderBookSnapshot(
        market_id="m1",
        bids=[OrderBookLevel(0.42, 1000), OrderBookLevel(0.41, 500)],
        asks=[OrderBookLevel(0.43, 800)],
        seq=1,
    )
    client.inject_for_testing(snap)
    assert client.latest("m1") is snap
    assert client.latest("m2").market_id == "m2"
    assert client.latest("ghost") is None


def test_snapshots_iterator_yields_injected():
    async def run() -> list[OrderBookSnapshot]:
        client = PolymarketL2Client(market_ids=["m1"])
        snap = OrderBookSnapshot(
            market_id="m1",
            bids=[OrderBookLevel(0.42, 1000)],
            asks=[OrderBookLevel(0.43, 800)],
            seq=1,
        )
        client.inject_for_testing(snap)

        out: list[OrderBookSnapshot] = []
        async for s in client.snapshots():
            out.append(s)
            if len(out) >= 1:
                break
        await client.close()
        return out

    out = asyncio.run(run())
    assert len(out) == 1
    assert out[0].market_id == "m1"
