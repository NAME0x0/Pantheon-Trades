"""Tests for the GDELT 2.0 Document API connector.

We never hit GDELT in tests — every external call goes through a stub
``AsyncClient`` so the suite is hermetic. The shape we stub is the
documented DOC API JSON envelope.
"""

from __future__ import annotations

import json

import pytest

from pythia.gdelt import GdeltSource, _fmt_gdelt_dt


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
    """Single-payload stub. Captures the params dict so we can assert
    that the GDELT API was called with the right query / mode /
    window."""

    def __init__(self, payloads: list[dict]):
        self._payloads = list(payloads)
        self.calls: list[dict] = []

    async def get(self, url: str, *, params: dict | None = None, timeout: float = 20.0):
        self.calls.append(params or {})
        # Cycle through queued payloads. If we run out, repeat last.
        payload = self._payloads.pop(0) if self._payloads else {}
        return _StubResp(200, payload)


@pytest.mark.asyncio
async def test_fmt_gdelt_dt_is_utc_yyyymmddhhmmss():
    """GDELT requires UTC YYYYMMDDhhmmss with no separators."""
    from datetime import datetime, timezone

    s = _fmt_gdelt_dt(datetime(2026, 5, 17, 9, 30, 15, tzinfo=timezone.utc))
    assert s == "20260517093015"
    assert len(s) == 14


@pytest.mark.asyncio
async def test_fetch_returns_default_query_snapshot():
    client = _StubClient([{"timeline": [{"datetime": "20260517090000", "value": 12}]}])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    snap = await src.fetch()
    assert snap.source == "gdelt"
    assert snap.data["query"] == GdeltSource.DEFAULT_QUERY
    assert snap.data["mode"] == "timelinevol"
    assert len(snap.data["timeline"]) == 1


@pytest.mark.asyncio
async def test_timeline_passes_query_and_mode_to_api():
    """The DOC API call should receive the user's query, mode, and a
    14-char start/end window."""
    client = _StubClient([{"timeline": []}])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    await src.timeline("theme:PROTEST AND sourcecountry:US", mode="timelinetone", hours=12)
    assert len(client.calls) == 1
    params = client.calls[0]
    assert params["query"] == "theme:PROTEST AND sourcecountry:US"
    assert params["mode"] == "timelinetone"
    assert params["format"] == "json"
    assert len(params["startdatetime"]) == 14
    assert len(params["enddatetime"]) == 14
    assert params["startdatetime"] < params["enddatetime"]


@pytest.mark.asyncio
async def test_article_count_sums_timeline_values():
    """Total article count = sum of bucketed values."""
    payload = {"timeline": [
        {"datetime": "20260517000000", "value": 5},
        {"datetime": "20260517010000", "value": 7},
        {"datetime": "20260517020000", "value": 13},
    ]}
    client = _StubClient([payload])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    n = await src.article_count("anything", hours=3)
    assert n == 25


@pytest.mark.asyncio
async def test_article_count_empty_returns_zero():
    client = _StubClient([{"timeline": []}])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    assert await src.article_count("anything") == 0


@pytest.mark.asyncio
async def test_average_tone_volume_weighted():
    """Tone average must weight by article count, not equally."""
    payload = {"timeline": [
        # 80% volume at tone +5, 20% volume at tone -10 → weighted ~+2
        {"datetime": "20260517000000", "value": 80, "tone": 5.0},
        {"datetime": "20260517010000", "value": 20, "tone": -10.0},
    ]}
    client = _StubClient([payload])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    tone = await src.average_tone("anything")
    # (80*5 + 20*(-10)) / 100 = (400 - 200) / 100 = 2.0
    assert abs(tone - 2.0) < 1e-6


@pytest.mark.asyncio
async def test_average_tone_returns_none_when_empty():
    client = _StubClient([{"timeline": []}])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    assert await src.average_tone("anything") is None


@pytest.mark.asyncio
async def test_geopolitical_risk_combines_volume_and_tone():
    """High volume + negative tone → risk score near 1.

    The compositor calls article_count (volume mode) then average_tone
    (volinfo mode). Stub two payloads accordingly.
    """
    high_vol = {"timeline": [
        {"datetime": "20260517000000", "value": 200, "tone": -15.0},
    ]}
    high_vol_info = {"timeline": [
        {"datetime": "20260517000000", "value": 200, "tone": -15.0},
    ]}
    client = _StubClient([high_vol, high_vol_info])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    out = await src.geopolitical_risk("UA", hours=72)
    assert out["country"] == "UA"
    assert out["article_count"] == 200
    # high vol + very negative tone → risk > 0.85
    assert out["risk_score"] > 0.85


@pytest.mark.asyncio
async def test_geopolitical_risk_neutral_when_no_coverage():
    """No articles → moderate risk score (neutral tone default)."""
    empty = {"timeline": []}
    client = _StubClient([empty, empty])
    src = GdeltSource(client=client)  # type: ignore[arg-type]
    out = await src.geopolitical_risk("CH", hours=72)
    assert out["article_count"] == 0
    assert out["tone"] is None
    # vol_part=0 + tone_part=0.5 (neutral default) → risk = 0.25
    assert 0.2 < out["risk_score"] < 0.3
