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
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

DEFAULT_INSTANCES: tuple[str, ...] = (
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.net",
)

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
) -> list[Tweet]:
    """Return up to ``max_results`` recent tweets matching ``query``.

    Tries each instance in order until one returns a 200 with a body
    that parses as RSS. Empty list if every instance fails.
    """
    if not query.strip():
        return []
    client = http_client or _default_client()
    for base in instances:
        url = f"{base.rstrip('/')}/search/rss?f=tweets&q={_url_encode(query)}"
        try:
            resp = client.get(url, timeout=10.0)
        except Exception:  # noqa: BLE001
            continue
        if getattr(resp, "status_code", 0) != 200:
            continue
        body = getattr(resp, "text", "")
        if not body:
            continue
        try:
            tweets = _parse_rss(body)
        except Exception:  # noqa: BLE001
            continue
        return tweets[:max_results]
    return []


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
