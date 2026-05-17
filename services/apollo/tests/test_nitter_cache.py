"""Tests for the Nitter TTL cache + graceful sentiment fallback."""

from __future__ import annotations

import time


from apollo.sources.nitter import (
    DEFAULT_CACHE_TTL_SECONDS,
    _cache_clear,
    fetch_recent_tweets,
    graceful_sentiment_score,
)


class _FakeResp:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class _CountingClient:
    """Counts ``get`` invocations so we can verify cache hits."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, *, timeout=10.0):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return _FakeResp(503, "")


_VALID_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>tweet one</title>
    <link>https://nitter.host/alice/status/1</link>
    <description>This is a great tweet</description>
    <pubDate>Mon, 17 May 2026 14:33:00 +0000</pubDate>
  </item>
</channel>
</rss>"""


def setup_function(_func):
    """Clear the module-level cache between tests."""
    _cache_clear()


def test_cache_hit_avoids_second_network_call():
    client = _CountingClient([_FakeResp(200, _VALID_RSS), _FakeResp(200, _VALID_RSS)])
    out1 = fetch_recent_tweets("bitcoin", http_client=client, instances=("https://x",))
    out2 = fetch_recent_tweets("bitcoin", http_client=client, instances=("https://x",))
    assert len(out1) == 1
    assert len(out2) == 1
    # Cache hit on second call ⇒ only one get
    assert client.calls == 1


def test_bypass_cache_forces_refetch():
    client = _CountingClient([_FakeResp(200, _VALID_RSS), _FakeResp(200, _VALID_RSS)])
    fetch_recent_tweets("bitcoin", http_client=client, instances=("https://x",))
    fetch_recent_tweets(
        "bitcoin", http_client=client, instances=("https://x",),
        bypass_cache=True,
    )
    assert client.calls == 2


def test_cache_isolated_by_query():
    """Different query strings hash to different cache keys."""
    client = _CountingClient([
        _FakeResp(200, _VALID_RSS),
        _FakeResp(200, _VALID_RSS),
    ])
    fetch_recent_tweets("bitcoin", http_client=client, instances=("https://x",))
    fetch_recent_tweets("ethereum", http_client=client, instances=("https://x",))
    assert client.calls == 2


def test_cache_expires_after_ttl():
    """When cache_ttl_seconds elapses, the next call refetches."""
    client = _CountingClient([
        _FakeResp(200, _VALID_RSS),
        _FakeResp(200, _VALID_RSS),
    ])
    fetch_recent_tweets(
        "btc", http_client=client, instances=("https://x",),
        cache_ttl_seconds=0.01,  # 10ms
    )
    time.sleep(0.05)  # past TTL
    fetch_recent_tweets(
        "btc", http_client=client, instances=("https://x",),
        cache_ttl_seconds=0.01,
    )
    assert client.calls == 2


def test_empty_results_not_cached():
    """A 200 with empty RSS body ⇒ no cache entry; next call retries."""
    empty_rss = """<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>"""
    client = _CountingClient([
        _FakeResp(200, empty_rss),
        _FakeResp(200, _VALID_RSS),
    ])
    out1 = fetch_recent_tweets("x", http_client=client, instances=("https://x",))
    out2 = fetch_recent_tweets("x", http_client=client, instances=("https://x",))
    assert out1 == []
    assert len(out2) == 1
    assert client.calls == 2


def test_502_falls_through_to_next_instance():
    """First instance returns 502, second returns 200 ⇒ tweets returned."""
    client = _CountingClient([
        _FakeResp(502, ""),
        _FakeResp(200, _VALID_RSS),
    ])
    out = fetch_recent_tweets(
        "bitcoin", http_client=client,
        instances=("https://dead", "https://alive"),
    )
    assert len(out) == 1


def test_all_instances_dead_returns_empty():
    client = _CountingClient([
        _FakeResp(502, ""),
        _FakeResp(503, ""),
        _FakeResp(504, ""),
    ])
    out = fetch_recent_tweets(
        "bitcoin", http_client=client,
        instances=("https://a", "https://b", "https://c"),
    )
    assert out == []


def test_graceful_sentiment_neutral_when_all_dead():
    """When every Nitter instance fails ⇒ neutral fallback 0.5."""
    client = _CountingClient([_FakeResp(503, ""), _FakeResp(503, "")])
    score = graceful_sentiment_score(
        "bitcoin", http_client=client,
        instances=("https://a", "https://b"),
        neutral_fallback=0.5,
    )
    assert score == 0.5


def test_graceful_sentiment_when_aggregate_raises():
    """If the sentiment aggregator throws, we still return the fallback."""
    client = _CountingClient([_FakeResp(200, _VALID_RSS)])
    # Patch crowd_sentiment.aggregate to raise.
    import apollo.features.crowd_sentiment as cs

    orig = cs.aggregate
    cs.aggregate = lambda _tweets: (_ for _ in ()).throw(RuntimeError("bad"))
    try:
        score = graceful_sentiment_score(
            "bitcoin", http_client=client,
            instances=("https://a",),
            neutral_fallback=0.42,
        )
        assert score == 0.42
    finally:
        cs.aggregate = orig


def test_default_ttl_constant_value():
    assert DEFAULT_CACHE_TTL_SECONDS == 30 * 60
