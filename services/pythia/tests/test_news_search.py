"""Tests for the targeted news-search module.

We do not hit Brave or GDELT in CI; both calls are stubbed via
``monkeypatch`` so the parser logic is exercised against representative
payload shapes.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx

from pythia import news_search


def _make_response(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        request=httpx.Request("GET", "http://test"),
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


def test_format_for_prompt_handles_empty():
    assert news_search.format_for_prompt([]) == "(no recent news)"


def test_format_for_prompt_renders_hit():
    hit = news_search.NewsHit(
        title="Fed pauses",
        url="https://reuters.com/x",
        snippet="rate decision",
        published_at=datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc),
        source="reuters.com",
        backend="brave",
    )
    out = news_search.format_for_prompt([hit])
    assert "Fed pauses" in out
    assert "reuters.com" in out
    assert "rate decision" in out
    assert "2026-05-16 10:00 UTC" in out


def test_brave_parses_results(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "brv-test")

    async def fake_get(self, url, **kw):
        return _make_response(
            {
                "results": [
                    {
                        "title": "Fed pauses",
                        "url": "https://reuters.com/x",
                        "description": "rate decision",
                        "meta_url": {"hostname": "reuters.com"},
                    },
                    {
                        "title": "BTC surges",
                        "url": "https://bloomberg.com/y",
                        "description": "above 110k",
                        "meta_url": {"hostname": "bloomberg.com"},
                    },
                ]
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    out = asyncio.run(news_search.search("Bitcoin", limit=5, hours=24))
    assert len(out) == 2
    assert out[0].title == "Fed pauses"
    assert out[0].source == "reuters.com"
    assert out[0].backend == "brave"


def test_falls_back_to_gdelt_when_no_brave_key(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    async def fake_get(self, url, **kw):
        return _make_response(
            {
                "articles": [
                    {
                        "title": "BTC daily wrap",
                        "url": "https://example.com/a",
                        "seendate": "20260516T100000Z",
                        "domain": "example.com",
                    }
                ]
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    out = asyncio.run(news_search.search("Bitcoin", limit=3, hours=24))
    assert len(out) == 1
    assert out[0].source == "example.com"
    assert out[0].backend == "gdelt"
    assert out[0].published_at == datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)


def test_returns_empty_on_total_failure(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    async def fake_get(self, url, **kw):
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    out = asyncio.run(news_search.search("Bitcoin"))
    assert out == []
