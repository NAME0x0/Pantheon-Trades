"""Tests for the extended DeFiLlama endpoints."""

from __future__ import annotations

import pytest

from pythia.defillama import DefiLlamaSource


class _StubResp:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _StubClient:
    def __init__(self, mapping: dict):
        self._mapping = mapping
        self.calls: list[str] = []

    async def get(self, url: str, *, params: dict | None = None, timeout: float = 10.0):
        self.calls.append(url)
        for key, resp in self._mapping.items():
            if url.endswith(key) or key in url:
                return resp
        raise RuntimeError(f"no stub for {url}")


@pytest.mark.asyncio
async def test_chains_returns_list():
    stub = _StubClient({
        "/v2/chains": _StubResp(200, [{"name": "Ethereum", "tvl": 1e10}]),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    chains = await src.chains()
    assert chains[0]["name"] == "Ethereum"


@pytest.mark.asyncio
async def test_chains_handles_non_list():
    stub = _StubClient({"/v2/chains": _StubResp(200, {"unexpected": True})})
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    assert await src.chains() == []


@pytest.mark.asyncio
async def test_chain_tvl_known():
    stub = _StubClient({
        "/v2/chains": _StubResp(200, [{"name": "Ethereum", "tvl": 5e10}]),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    tvl = await src.chain_tvl("ethereum")
    assert tvl == 5e10


@pytest.mark.asyncio
async def test_chain_tvl_unknown_returns_zero():
    stub = _StubClient({
        "/v2/chains": _StubResp(200, [{"name": "Ethereum", "tvl": 5e10}]),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    assert await src.chain_tvl("doesnotexist") == 0.0


@pytest.mark.asyncio
async def test_stablecoin_total_sums_pegged_usd():
    stub = _StubClient({
        "/stablecoins": _StubResp(200, {
            "peggedAssets": [
                {"circulating": {"peggedUSD": 100_000_000_000}},
                {"circulating": {"peggedUSD": 50_000_000_000}},
                {"circulating": {"peggedUSD": "not-a-number"}},
                {"circulating": {}},
            ]
        }),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    total = await src.stablecoin_total_marketcap()
    assert total == 150_000_000_000


@pytest.mark.asyncio
async def test_pool_yields_unwraps_data_field():
    stub = _StubClient({
        "/pools": _StubResp(200, {"status": "success", "data": [{"apy": 5.0}]}),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    pools = await src.pool_yields()
    assert pools == [{"apy": 5.0}]


@pytest.mark.asyncio
async def test_pool_yields_handles_flat_list():
    stub = _StubClient({
        "/pools": _StubResp(200, [{"apy": 5.0}]),
    })
    src = DefiLlamaSource(client=stub)  # type: ignore[arg-type]
    pools = await src.pool_yields()
    assert pools == [{"apy": 5.0}]
