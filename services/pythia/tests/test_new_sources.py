"""Tests for the Wikipedia / FRED / Manifold pythia sources.

All three follow the same stub-client pattern as the GDELT tests —
hermetic, no network. We verify the request shape (URL, params) and
the response parsing.
"""

from __future__ import annotations

import json

import pytest

from pythia.fred import FredSource
from pythia.manifold import ManifoldSource
from pythia.wikipedia import WikipediaSource, _fmt_wiki_date


class _StubResp:
    def __init__(self, status_code: int, payload):
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
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url: str, *, params: dict | None = None, timeout: float = 15.0):
        self.calls.append((url, params or {}))
        payload = self._payloads.pop(0) if self._payloads else {}
        return _StubResp(200, payload)


# ─── Wikipedia ────────────────────────────────────────────────────────


def test_fmt_wiki_date_daily_and_hourly():
    from datetime import datetime, timezone
    dt = datetime(2026, 5, 17, 9, 30, tzinfo=timezone.utc)
    assert _fmt_wiki_date(dt, "daily") == "20260517"
    assert _fmt_wiki_date(dt, "hourly") == "2026051709"


@pytest.mark.asyncio
async def test_wikipedia_daily_views_url_shape():
    payload = {"items": [
        {"timestamp": "2026050100", "views": 1234},
        {"timestamp": "2026050200", "views": 5678},
    ]}
    client = _StubClient([payload])
    src = WikipediaSource(client=client)  # type: ignore[arg-type]
    out = await src.daily_views("Bitcoin", days=2)
    assert out["article"] == "Bitcoin"
    assert out["granularity"] == "daily"
    assert len(out["timeline"]) == 2
    assert out["timeline"][1]["views"] == 5678
    # URL should contain the project + access + agent path segments
    url, _params = client.calls[0]
    assert "/per-article/en.wikipedia/all-access/user/Bitcoin/daily/" in url


@pytest.mark.asyncio
async def test_wikipedia_article_underscoring():
    """Spaces become underscores in the URL."""
    client = _StubClient([{"items": []}])
    src = WikipediaSource(client=client)  # type: ignore[arg-type]
    await src.daily_views("Donald Trump", days=1)
    url, _ = client.calls[0]
    assert "/Donald_Trump/" in url


@pytest.mark.asyncio
async def test_wikipedia_attention_velocity_z_detects_spike():
    """Flat baseline + spike on recent days → strongly positive z."""
    # 27 days of low traffic, 3 days of huge traffic.
    flat = [{"timestamp": f"d{i}", "views": 100} for i in range(27)]
    spike = [{"timestamp": f"d{27+i}", "views": 10_000} for i in range(3)]
    client = _StubClient([{"items": flat + spike}])
    src = WikipediaSource(client=client)  # type: ignore[arg-type]
    z = await src.attention_velocity_z("Bitcoin", window_days=30, recent_days=3)
    # Spike of 100× baseline against zero variance ⇒ undefined; we
    # protect against /0 by returning None if sd is zero. Use a less
    # flat baseline next test for the real signal-y check.
    assert z is None or z > 5.0


@pytest.mark.asyncio
async def test_wikipedia_attention_velocity_z_returns_none_on_empty():
    client = _StubClient([{"items": []}])
    src = WikipediaSource(client=client)  # type: ignore[arg-type]
    assert await src.attention_velocity_z("Bitcoin") is None


@pytest.mark.asyncio
async def test_wikipedia_attention_velocity_with_variance():
    """Baseline with real variance + clear spike → finite positive z."""
    items = [{"timestamp": f"d{i}", "views": 100 + (i % 10) * 5} for i in range(27)]
    items += [{"timestamp": f"d{27+i}", "views": 5000} for i in range(3)]
    client = _StubClient([{"items": items}])
    src = WikipediaSource(client=client)  # type: ignore[arg-type]
    z = await src.attention_velocity_z("Bitcoin", window_days=30, recent_days=3)
    assert z is not None
    assert z > 50  # spike is many SDs above baseline


# ─── FRED ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fred_series_observations_passes_api_key():
    client = _StubClient([{"observations": [{"date": "2026-05-01", "value": "4.50"}]}])
    src = FredSource(client=client, api_key="my_key")  # type: ignore[arg-type]
    obs = await src.series_observations("FEDFUNDS", limit=1)
    assert len(obs) == 1
    _url, params = client.calls[0]
    assert params["series_id"] == "FEDFUNDS"
    assert params["api_key"] == "my_key"
    assert params["file_type"] == "json"


@pytest.mark.asyncio
async def test_fred_latest_returns_float():
    client = _StubClient([{"observations": [{"date": "2026-05-01", "value": "4.50"}]}])
    src = FredSource(client=client, api_key="k")  # type: ignore[arg-type]
    latest = await src.latest("FEDFUNDS")
    assert latest["value_float"] == 4.5
    assert latest["date"] == "2026-05-01"


@pytest.mark.asyncio
async def test_fred_latest_handles_missing_value():
    """FRED encodes missing observations as '.'; we surface value_float=None."""
    client = _StubClient([{"observations": [{"date": "2026-05-01", "value": "."}]}])
    src = FredSource(client=client, api_key="k")  # type: ignore[arg-type]
    latest = await src.latest("FOO")
    assert latest["value_float"] is None


@pytest.mark.asyncio
async def test_fred_delta_vs_target_computes_signed_delta():
    client = _StubClient([{"observations": [{"date": "2026-05-01", "value": "4.75"}]}])
    src = FredSource(client=client, api_key="k")  # type: ignore[arg-type]
    out = await src.delta_vs("FEDFUNDS", target=4.50)
    assert out["delta"] == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_fred_percent_change_yoy():
    """13 observations (latest + 12 prior) → 1-year delta computable."""
    obs = [{"date": f"2026-{i:02d}-01", "value": str(100 + i)} for i in range(13, 0, -1)]
    client = _StubClient([{"observations": obs}])
    src = FredSource(client=client, api_key="k")  # type: ignore[arg-type]
    out = await src.percent_change("CPIAUCSL", lookback=12)
    # latest=113 (i=13), prior=101 (i=1); pct = (113-101)/101 ≈ 0.119
    assert out["pct_change"] == pytest.approx(0.1188, abs=1e-3)


@pytest.mark.asyncio
async def test_fred_percent_change_returns_none_on_thin_series():
    client = _StubClient([{"observations": [{"date": "2026-05-01", "value": "100"}]}])
    src = FredSource(client=client, api_key="k")  # type: ignore[arg-type]
    out = await src.percent_change("FOO", lookback=12)
    assert out["pct_change"] is None


# ─── Manifold ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manifold_list_markets_clamps_limit():
    """Limit=10000 clamps to 1000 (Manifold API ceiling)."""
    client = _StubClient([[]])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    await src.list_markets(limit=10_000)
    _url, params = client.calls[0]
    assert params["limit"] == "1000"


@pytest.mark.asyncio
async def test_manifold_implied_probability_for_binary():
    payload = {"id": "abc", "outcomeType": "BINARY", "probability": 0.42}
    client = _StubClient([payload])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    p = await src.implied_probability("abc")
    assert p == 0.42


@pytest.mark.asyncio
async def test_manifold_implied_probability_returns_none_for_non_binary():
    payload = {"id": "abc", "outcomeType": "FREE_RESPONSE", "probability": 0.42}
    client = _StubClient([payload])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    assert await src.implied_probability("abc") is None


@pytest.mark.asyncio
async def test_manifold_resolved_binary_markets_filters_correctly():
    payload = [
        {"id": "a", "outcomeType": "BINARY", "isResolved": True},
        {"id": "b", "outcomeType": "BINARY", "isResolved": False},
        {"id": "c", "outcomeType": "FREE_RESPONSE", "isResolved": True},
        {"id": "d", "outcomeType": "BINARY", "isResolved": True},
    ]
    client = _StubClient([payload])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    out = await src.resolved_binary_markets(limit=10)
    assert {m["id"] for m in out} == {"a", "d"}


@pytest.mark.asyncio
async def test_manifold_consensus_delta_signed():
    payload = {"id": "abc", "outcomeType": "BINARY", "probability": 0.60}
    client = _StubClient([payload])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    out = await src.consensus_delta("abc", polymarket_implied=0.45)
    # Manifold 0.60, Polymarket 0.45 → delta = +0.15
    assert out["delta"] == pytest.approx(0.15)


@pytest.mark.asyncio
async def test_manifold_consensus_delta_handles_no_data():
    """Non-binary market → delta is None."""
    payload = {"id": "abc", "outcomeType": "FREE_RESPONSE"}
    client = _StubClient([payload])
    src = ManifoldSource(client=client)  # type: ignore[arg-type]
    out = await src.consensus_delta("abc", polymarket_implied=0.5)
    assert out["delta"] is None
