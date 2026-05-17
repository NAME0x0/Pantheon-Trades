"""Tests for the three new edge-source pythia connectors:
- odds_api (sportsbook + politics consensus)
- perps (Binance funding + OI)
- cftc (commitments of traders)

All hermetic. Stubbed clients, no network."""

from __future__ import annotations


import pytest

from pythia.cftc import CftcSource
from pythia.odds_api import (
    OddsApiSource,
    american_to_prob,
    decimal_to_prob,
    vig_free,
)
from pythia.perps import BinancePerpsSource


class _StubResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _StubClient:
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []

    async def get(self, url, *, params=None, timeout=10.0):
        self.calls.append((url, params or {}))
        payload = self._payloads.pop(0) if self._payloads else {}
        return _StubResp(200, payload)


# ─── Odds API math ────────────────────────────────────────────────────


def test_american_to_prob_positive():
    """+150 → 40%."""
    assert american_to_prob(150) == pytest.approx(0.40)


def test_american_to_prob_negative():
    """-110 → ~52.4%."""
    assert american_to_prob(-110) == pytest.approx(0.5238, abs=0.001)


def test_decimal_to_prob():
    """2.0 → 50%."""
    assert decimal_to_prob(2.0) == 0.50
    assert decimal_to_prob(4.0) == 0.25


def test_decimal_to_prob_invalid():
    """odds <= 1.0 → 0."""
    assert decimal_to_prob(0.5) == 0.0
    assert decimal_to_prob(1.0) == 0.0


def test_vig_free_strips_overround():
    """Two outcomes summing to 1.05 → each scaled down by 1/1.05."""
    out = vig_free([0.55, 0.50])
    assert sum(out) == pytest.approx(1.0)
    assert out[0] == pytest.approx(0.55 / 1.05)


def test_vig_free_zero_total_falls_back():
    """No data → uniform prior."""
    out = vig_free([0.0, 0.0])
    assert out == [0.5, 0.5]


# ─── Odds API client ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_odds_api_events_passes_params():
    client = _StubClient([[]])
    src = OddsApiSource(client=client, api_key="test-key")  # type: ignore[arg-type]
    await src.events(sport="americanfootball_nfl", markets=("h2h",), regions=("us",))
    url, params = client.calls[0]
    assert "americanfootball_nfl" in url
    assert params["apiKey"] == "test-key"
    assert params["regions"] == "us"
    assert params["markets"] == "h2h"


@pytest.mark.asyncio
async def test_odds_api_consensus_returns_none_when_no_events():
    client = _StubClient([[]])
    src = OddsApiSource(client=client, api_key="k")  # type: ignore[arg-type]
    out = await src.consensus_probability(sport="x", team_name="Lakers")
    assert out is None


@pytest.mark.asyncio
async def test_odds_api_consensus_averages_across_books():
    """3 books all listing 2.0 for Lakers → 50/50 vig-free → 0.50 consensus."""
    event = {
        "id": "ev1",
        "bookmakers": [
            {
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Lakers", "price": 2.0},
                            {"name": "Celtics", "price": 2.0},
                        ],
                    }
                ]
            },
            {
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Lakers", "price": 1.95},
                            {"name": "Celtics", "price": 1.95},
                        ],
                    }
                ]
            },
        ],
    }
    client = _StubClient([[event]])
    src = OddsApiSource(client=client, api_key="k")  # type: ignore[arg-type]
    out = await src.consensus_probability(sport="x", team_name="Lakers")
    assert out is not None
    assert out["team"] == "Lakers"
    # All books symmetric at ~50/50 → consensus ~0.50.
    assert out["p_yes"] == pytest.approx(0.50, abs=0.01)
    assert out["n_books"] == 2


# ─── Binance perps ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perps_funding_rate_parsing():
    client = _StubClient([{
        "symbol": "BTCUSDT",
        "lastFundingRate": "0.0001",
        "markPrice": "85000.0",
        "nextFundingTime": 1700000000000,
    }])
    src = BinancePerpsSource(client=client)  # type: ignore[arg-type]
    out = await src.funding_rate("BTCUSDT")
    assert out["symbol"] == "BTCUSDT"
    assert out["last_funding_rate"] == pytest.approx(0.0001)
    assert out["mark_price"] == 85000.0


@pytest.mark.asyncio
async def test_perps_funding_z_basic():
    """30 historical samples + 1 latest. Z of latest must be a float."""
    history = [
        {"fundingTime": 1000 + i, "fundingRate": str(0.0001 * (i - 15))}
        for i in range(30)
    ]
    latest = [{"fundingTime": 1100, "fundingRate": "0.005"}]
    client = _StubClient([history + latest])
    src = BinancePerpsSource(client=client)  # type: ignore[arg-type]
    z = await src.funding_z("BTCUSDT", window=30)
    # Latest is much higher than the small-magnitude history → positive z.
    assert z is not None
    assert z > 1.0


@pytest.mark.asyncio
async def test_perps_funding_z_too_few_samples():
    client = _StubClient([[{"fundingTime": 1, "fundingRate": "0.0001"}]])
    src = BinancePerpsSource(client=client)  # type: ignore[arg-type]
    z = await src.funding_z("BTCUSDT", window=30)
    assert z is None


@pytest.mark.asyncio
async def test_perps_open_interest_parsing():
    client = _StubClient([{"symbol": "BTCUSDT", "openInterest": "12345.6", "time": 1700000000000}])
    src = BinancePerpsSource(client=client)  # type: ignore[arg-type]
    out = await src.open_interest("BTCUSDT")
    assert out["open_interest"] == pytest.approx(12345.6)


# ─── CFTC source ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cftc_latest_positioning_parses_net():
    """commercial_long - commercial_short = commercial_net."""
    payload = [{
        "market_and_exchange_names": "BITCOIN - CME",
        "report_date_as_yyyy_mm_dd": "2026-05-13",
        "comm_positions_long_all": "500",
        "comm_positions_short_all": "300",
        "noncomm_positions_long_all": "1000",
        "noncomm_positions_short_all": "800",
        "open_interest_all": "5000",
    }]
    client = _StubClient([payload])
    src = CftcSource(client=client)  # type: ignore[arg-type]
    out = await src.latest_positioning("BITCOIN")
    assert out["commercial_net"] == 200.0
    assert out["non_commercial_net"] == 200.0
    assert out["open_interest"] == 5000.0


@pytest.mark.asyncio
async def test_cftc_latest_positioning_none_when_empty():
    client = _StubClient([[]])
    src = CftcSource(client=client)  # type: ignore[arg-type]
    assert await src.latest_positioning("XYZ") is None


@pytest.mark.asyncio
async def test_cftc_positioning_z_detects_crowded_longs():
    """Latest report has much-higher non-comm net than the 26-week history.

    The 26 historical rows are given small natural variance so sd > 0;
    a zero-variance history would (correctly) return None per the
    source's sd <= 0 guard."""
    rows = []
    for i in range(26):
        # Wobble around net=100 with ±20 variance
        long = 1000 + (i % 5) * 8
        short = 900 + (i % 7) * 5
        rows.append({
            "noncomm_positions_long_all": str(long),
            "noncomm_positions_short_all": str(short),
        })
    crowded = {
        "noncomm_positions_long_all": "5000",
        "noncomm_positions_short_all": "1000",  # net 4000 — far outlier
    }
    payload = [crowded] + rows
    client = _StubClient([payload])
    src = CftcSource(client=client)  # type: ignore[arg-type]
    z = await src.positioning_z("BTC", window=26)
    assert z is not None
    assert z > 5.0  # extreme outlier


@pytest.mark.asyncio
async def test_cftc_positioning_z_returns_none_on_thin_history():
    client = _StubClient([[{"noncomm_positions_long_all": "1", "noncomm_positions_short_all": "0"}]])
    src = CftcSource(client=client)  # type: ignore[arg-type]
    assert await src.positioning_z("X", window=26) is None
