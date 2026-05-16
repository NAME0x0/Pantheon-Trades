"""Targeted news search — fetches recent articles matching a market query.

Two backends, in priority order:

  1. Brave Search API — best signal, requires BRAVE_API_KEY. Free tier
     covers ~2000 queries/month.
  2. GDELT 2.0 DOC API — free, no key required, indexes worldwide
     news with rich metadata.

Both return the same shape: ``list[NewsHit]`` with title, url, snippet,
published_at, source. Apollo embeds the top N hits into the Signal
envelope so council agents see fresh news as part of the prompt,
without needing a function-calling refactor of the LLM protocol.

Network failure is non-fatal — the function returns an empty list and
the council deliberates against the signal alone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

log = structlog.get_logger("pythia.news_search")

BRAVE_API = "https://api.search.brave.com/res/v1/news/search"
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_TIMEOUT = float(os.environ.get("NEWS_SEARCH_TIMEOUT_S", "8"))


@dataclass(frozen=True)
class NewsHit:
    title: str
    url: str
    snippet: str
    published_at: Optional[datetime]
    source: str  # e.g. "reuters.com"
    backend: str  # "brave" or "gdelt"


async def search(query: str, limit: int = 5, hours: int = 48) -> list[NewsHit]:
    """Return up to ``limit`` recent news hits for ``query``.

    Tries Brave first if BRAVE_API_KEY is set; falls back to GDELT.
    Both backends respect a soft recency filter (``hours``).
    """
    if not query.strip():
        return []
    brave_key = os.environ.get("BRAVE_API_KEY", "").strip()
    if brave_key:
        try:
            hits = await _brave(query, limit, hours, brave_key)
            if hits:
                return hits
        except Exception as e:  # noqa: BLE001
            log.warning("pythia.news.brave_failed", error=str(e))
    try:
        return await _gdelt(query, limit, hours)
    except Exception as e:  # noqa: BLE001
        log.warning("pythia.news.gdelt_failed", error=str(e))
        return []


async def _brave(query: str, limit: int, hours: int, api_key: str) -> list[NewsHit]:
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": min(max(limit, 1), 20),
        "freshness": "pd" if hours <= 24 else "pw" if hours <= 168 else "pm",
        "safesearch": "moderate",
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http:
        r = await http.get(BRAVE_API, headers=headers, params=params)
        r.raise_for_status()
        payload = r.json()
    results = (payload.get("results") or [])[:limit]
    hits: list[NewsHit] = []
    for item in results:
        ts: Optional[datetime] = None
        ts_raw = item.get("page_age") or item.get("age")
        if ts_raw:
            try:
                # Brave sometimes returns ISO, sometimes natural-language age.
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                ts = None
        host = ""
        meta_url = item.get("meta_url") or {}
        if isinstance(meta_url, dict):
            host = (meta_url.get("hostname") or meta_url.get("netloc") or "").strip()
        hits.append(
            NewsHit(
                title=(item.get("title") or "").strip(),
                url=(item.get("url") or "").strip(),
                snippet=(item.get("description") or item.get("snippet") or "").strip(),
                published_at=ts,
                source=host or _host_from_url(item.get("url", "")),
                backend="brave",
            )
        )
    return hits


async def _gdelt(query: str, limit: int, hours: int) -> list[NewsHit]:
    # GDELT 2.0 expects a structured query string.
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": min(max(limit, 1), 50),
        "timespan": f"{hours}h",
        "sort": "DateDesc",
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http:
        r = await http.get(GDELT_API, params=params)
        r.raise_for_status()
        payload = r.json()
    articles = (payload.get("articles") or [])[:limit]
    hits: list[NewsHit] = []
    for item in articles:
        ts: Optional[datetime] = None
        ts_raw = item.get("seendate")  # format: YYYYMMDDTHHMMSSZ
        if ts_raw:
            try:
                ts = datetime.strptime(ts_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                ts = None
        hits.append(
            NewsHit(
                title=(item.get("title") or "").strip(),
                url=(item.get("url") or "").strip(),
                snippet="",  # GDELT ArtList does not include snippets
                published_at=ts,
                source=(item.get("domain") or "").strip(),
                backend="gdelt",
            )
        )
    return hits


def _host_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or ""
    except Exception:  # noqa: BLE001
        return ""


def format_for_prompt(hits: list[NewsHit]) -> str:
    """Render hits as a compact prompt block agents can read."""
    if not hits:
        return "(no recent news)"
    lines = []
    for h in hits:
        when = h.published_at.strftime("%Y-%m-%d %H:%M UTC") if h.published_at else "?"
        line = f"- [{when}] {h.source} — {h.title}"
        if h.snippet:
            line += f"\n  {h.snippet[:240]}"
        lines.append(line)
    return "\n".join(lines)
