"""Tests for the Nitter RSS scraper + lexicon-based sentiment scorer."""

from __future__ import annotations

from datetime import datetime, timezone

from apollo.features.crowd_sentiment import (
    CrowdSentiment,
    aggregate,
    score_text,
)
from apollo.sources.nitter import Tweet, _parse_rss, fetch_recent_tweets


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Nitter</title>
    <item>
      <link>https://nitter.test/elonmusk/status/1</link>
      <title>moon coming</title>
      <description>Bitcoin to the moon! Bullish breakout incoming.</description>
      <pubDate>Sat, 16 May 2026 14:33:00 +0000</pubDate>
      <dc:creator>elonmusk</dc:creator>
    </item>
    <item>
      <link>https://nitter.test/bear/status/2</link>
      <title>crash incoming</title>
      <description>This is going to crash hard. Total scam.</description>
      <pubDate>Sat, 16 May 2026 14:34:00 +0000</pubDate>
      <dc:creator>bear</dc:creator>
    </item>
  </channel>
</rss>"""


class _StubResp:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class _StubClient:
    def __init__(self, responses: dict[str, _StubResp]):
        self._responses = responses
        self.calls: list[str] = []

    def get(self, url: str, *, timeout: float = 10.0) -> _StubResp:
        self.calls.append(url)
        for base, resp in self._responses.items():
            if url.startswith(base):
                return resp
        raise RuntimeError("no stub for URL")


def test_parse_rss_extracts_items():
    tweets = _parse_rss(SAMPLE_RSS)
    assert len(tweets) == 2
    assert tweets[0].author == "elonmusk"
    assert "moon" in tweets[0].text.lower()
    assert tweets[0].published_at.tzinfo is not None


def test_tweet_clean_text_strips_tags():
    t = Tweet(
        text="<a href='x'>hello</a>  <br/> world  ",
        author="x",
        published_at=datetime.now(timezone.utc),
        link="https://x.test",
    )
    assert t.clean_text == "hello world"


def test_fetch_returns_empty_on_blank_query():
    assert fetch_recent_tweets("", http_client=_StubClient({})) == []


def test_fetch_uses_first_working_instance():
    client = _StubClient({
        "https://nitter.dead": _StubResp(503, ""),
        "https://nitter.alive": _StubResp(200, SAMPLE_RSS),
    })
    tweets = fetch_recent_tweets(
        "btc",
        instances=("https://nitter.dead", "https://nitter.alive"),
        http_client=client,
    )
    assert len(tweets) == 2
    # First call hit dead, second succeeded.
    assert len(client.calls) == 2


def test_fetch_returns_empty_when_all_instances_fail():
    client = _StubClient({"https://nitter.a": _StubResp(503, "")})
    out = fetch_recent_tweets("btc", instances=("https://nitter.a",), http_client=client)
    assert out == []


def test_fetch_respects_max_results():
    client = _StubClient({"https://nitter.a": _StubResp(200, SAMPLE_RSS)})
    out = fetch_recent_tweets("btc", instances=("https://nitter.a",), http_client=client, max_results=1)
    assert len(out) == 1


def test_score_text_positive():
    assert score_text("This is bullish, moon incoming!") > 0


def test_score_text_negative():
    assert score_text("Total crash and scam, terrible") < 0


def test_score_text_neutral():
    assert -0.2 < score_text("a routine market update with no opinion") < 0.2


def test_score_text_negation_flips():
    pos = score_text("this is great")
    neg = score_text("this is not great")
    assert pos > 0
    assert neg < pos
    assert neg <= 0


def test_score_text_intensifier_amplifies():
    base = score_text("amazing")
    amped = score_text("extremely amazing")
    assert amped > base


def test_score_text_empty():
    assert score_text("") == 0.0
    assert score_text("   ") == 0.0


def test_aggregate_empty_returns_neutral():
    out = aggregate([])
    assert isinstance(out, CrowdSentiment)
    assert out.sample_count == 0
    assert out.mean_score == 0.0
    assert out.neutral_share == 1.0


def test_aggregate_distribution_sums_to_one():
    tweets = _parse_rss(SAMPLE_RSS)
    out = aggregate(tweets)
    assert out.sample_count == 2
    assert abs(out.positive_share + out.neutral_share + out.negative_share - 1.0) < 1e-9


def test_aggregate_mean_in_expected_direction():
    bullish = [Tweet(text="bullish moon great win", author="x", published_at=datetime.now(timezone.utc), link="")]
    bearish = [Tweet(text="dump crash scam terrible", author="x", published_at=datetime.now(timezone.utc), link="")]
    assert aggregate(bullish).mean_score > 0
    assert aggregate(bearish).mean_score < 0
