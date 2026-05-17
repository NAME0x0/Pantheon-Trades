"""X / Twitter crowd-sentiment feed via Nitter RSS.

Nitter is an open-source, MIT-licensed Twitter front-end that exposes
RSS for every search. We hit any of a configurable list of instances
until one responds; results are returned as plain dataclasses so the
caller can drop them straight into Apollo's sentiment feature pipeline.

No API key. No rate limit other than what the instance imposes.
Instances die regularly — the fallback list MUST be kept up to date
operationally (see docs/RUNBOOK_NITTER.md when one exists).

The module is intentionally hermetic in tests: callers pass a stub
``http_client`` to inject RSS payloads. The default path uses httpx
(already an Apollo dependency) but only at first use.
"""

from __future__ import annotations

import re
import time as _time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock as _RLock
from typing import Protocol, runtime_checkable

DEFAULT_INSTANCES: tuple[str, ...] = (
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.net",
)

# In-process TTL cache for Nitter fetches. Many production callers
# refresh sentiment for the same query repeatedly within minutes; we
# don't want to hammer fragile public instances when the data hasn't
# moved. Default 30-min TTL matches the empirical refresh cadence of
# the Apollo sentiment feature. Imports for the cache are at the top
# of this module (see `_time`, `_RLock`).

DEFAULT_CACHE_TTL_SECONDS = 30 * 60  # 30 min
_CACHE: dict[str, tuple[float, list["Tweet"]]] = {}
_CACHE_LOCK = _RLock()


def _cache_get(key: str, ttl: float) -> "list[Tweet] | None":
    """Return the cached tweets for ``key`` if still inside TTL."""
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        timestamp, tweets = entry
        if _time.time() - timestamp > ttl:
            _CACHE.pop(key, None)
            return None
        return list(tweets)


def _cache_put(key: str, tweets: "list[Tweet]") -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (_time.time(), list(tweets))


def _cache_clear() -> None:
    """Test-helper. Drops the entire cache."""
    with _CACHE_LOCK:
        _CACHE.clear()

# Strip HTML tags coarsely — Nitter sometimes embeds <a>, <br/>, etc.
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Tweet:
    text: str
    author: str
    published_at: datetime
    link: str

    @property
    def clean_text(self) -> str:
        no_tags = _TAG_RE.sub(" ", self.text)
        return _WHITESPACE_RE.sub(" ", no_tags).strip()


@runtime_checkable
class HttpClient(Protocol):
    def get(self, url: str, *, timeout: float = 10.0) -> "_Response": ...


@runtime_checkable
class _Response(Protocol):
    status_code: int

    @property
    def text(self) -> str: ...


def fetch_recent_tweets(
    query: str,
    *,
    instances: tuple[str, ...] = DEFAULT_INSTANCES,
    max_results: int = 50,
    http_client: HttpClient | None = None,
    cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    bypass_cache: bool = False,
) -> list[Tweet]:
    """Return up to ``max_results`` recent tweets matching ``query``.

    Tries each instance in order until one returns a 200 with a body
    that parses as RSS. Empty list if every instance fails.

    Results are cached in-process with a configurable TTL — default
    30 min. The cache key is the lowercase normalised query. Pass
    ``bypass_cache=True`` to force a refetch. The cache is *per-
    process* (not shared across workers); for distributed cache
    behaviour, layer Redis on top of this function externally.

    Empty results are NOT cached — a flaky Nitter instance returning
    an empty body shouldn't suppress future attempts.
    """
    q = (query or "").strip()
    if not q:
        return []
    cache_key = f"q::{q.lower()}::n={max_results}"
    if not bypass_cache:
        cached = _cache_get(cache_key, cache_ttl_seconds)
        if cached is not None:
            return cached[:max_results]

    client = http_client or _default_client()
    for base in instances:
        url = f"{base.rstrip('/')}/search/rss?f=tweets&q={_url_encode(q)}"
        try:
            resp = client.get(url, timeout=10.0)
        except Exception:  # noqa: BLE001
            continue
        status = getattr(resp, "status_code", 0)
        # On 5xx (server errors) we DO NOT cache — try the next instance.
        # On 4xx (client errors) we also fall through.
        if status != 200:
            continue
        body = getattr(resp, "text", "")
        if not body:
            continue
        try:
            tweets = _parse_rss(body)
        except Exception:  # noqa: BLE001
            continue
        out = tweets[:max_results]
        if out:
            # Only cache non-empty results. An empty parse is still a
            # signal of "instance returned 200 but didn't have what we
            # need" — we'd rather retry than serve emptiness from cache.
            _cache_put(cache_key, out)
        return out
    return []


def graceful_sentiment_score(
    query: str,
    *,
    instances: tuple[str, ...] = DEFAULT_INSTANCES,
    http_client: HttpClient | None = None,
    neutral_fallback: float = 0.5,
) -> float:
    """Robust sentiment in [0, 1] for ``query`` with graceful fallback.

    If every Nitter instance fails (502, dead, rate-limited), returns
    ``neutral_fallback`` (default 0.5 — neutral) instead of propagating
    a failure. The adopted ``crowd_sentiment`` feature uses this so
    Apollo's pipeline never breaks on flaky scraping.

    Uses the same TTL cache as ``fetch_recent_tweets`` so repeated
    calls within the cache window are free.
    """
    from apollo.features.crowd_sentiment import aggregate

    try:
        tweets = fetch_recent_tweets(query, instances=instances, http_client=http_client)
    except Exception:  # noqa: BLE001
        return neutral_fallback
    if not tweets:
        return neutral_fallback
    try:
        agg = aggregate(tweets)
        # aggregate returns CrowdSentiment with .score in [0, 1]
        return max(0.0, min(1.0, float(getattr(agg, "score", neutral_fallback))))
    except Exception:  # noqa: BLE001
        return neutral_fallback


def _default_client() -> HttpClient:
    import httpx

    return httpx.Client(follow_redirects=True)


def _url_encode(text: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(text)


def _parse_rss(body: str) -> list[Tweet]:
    root = ET.fromstring(body)
    channel = root.find("channel")
    if channel is None:
        return []
    out: list[Tweet] = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate")
        author = (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or "").strip()
        if not author and link:
            author = _extract_author_from_link(link)
        published = _parse_pubdate(pub)
        out.append(
            Tweet(
                text=description or title,
                author=author,
                published_at=published,
                link=link,
            )
        )
    return out


def _extract_author_from_link(link: str) -> str:
    # Nitter link format: https://nitter.host/<author>/status/<id>
    parts = link.split("/")
    if len(parts) >= 4:
        return parts[3]
    return ""


def _parse_pubdate(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    # RFC 2822: "Mon, 16 May 2026 14:33:00 +0000"
    from email.utils import parsedate_to_datetime

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
