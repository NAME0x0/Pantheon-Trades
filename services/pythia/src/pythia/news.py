"""News aggregator — RSS feed sampling with simple sentiment heuristics.

We deliberately stay vendor-agnostic and keep parsing tolerant of partial
feeds. The output is shaped to drop straight into Apollo's sentiment
feature: each headline becomes a polarity sample weighted by source trust.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot


@dataclass(frozen=True)
class NewsItem:
    title: str
    published: datetime
    source: str
    url: str | None = None


BULLISH_TERMS = {
    "surge", "rally", "soar", "bullish", "record", "breakthrough", "gain",
    "rise", "jump", "all-time high", "ath", "approve", "launch",
}
BEARISH_TERMS = {
    "crash", "plunge", "bearish", "decline", "selloff", "drop", "fall",
    "reject", "ban", "lawsuit", "hack", "exploit", "collapse",
}


def _polarity(title: str) -> float:
    """Tiny lexicon-based polarity in [-1, +1]; returns 0.0 if no terms match."""
    lower = title.lower()
    bull = sum(1 for term in BULLISH_TERMS if term in lower)
    bear = sum(1 for term in BEARISH_TERMS if term in lower)
    if bull == 0 and bear == 0:
        return 0.0
    return (bull - bear) / max(bull + bear, 1)


_ITEM_RX = re.compile(r"<item>(.*?)</item>", re.DOTALL | re.IGNORECASE)
_TITLE_RX = re.compile(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)


class NewsSource(DataSource):
    name = "news"
    max_staleness_seconds = 600

    def __init__(self, client: httpx.AsyncClient, feeds: list[str] | None = None) -> None:
        super().__init__(client)
        self._feeds = feeds or []

    async def fetch(self) -> SourceSnapshot:
        items: list[NewsItem] = []
        for feed in self._feeds:
            try:
                resp = await self._client.get(feed, timeout=10.0)
                resp.raise_for_status()
                for match in _ITEM_RX.finditer(resp.text):
                    title_m = _TITLE_RX.search(match.group(1))
                    if not title_m:
                        continue
                    title = (title_m.group(1) or title_m.group(2) or "").strip()
                    if not title:
                        continue
                    items.append(
                        NewsItem(title=title, published=utc_now(), source=feed)
                    )
            except httpx.HTTPError:
                continue
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={
                "items": [
                    {"title": i.title, "polarity": _polarity(i.title), "source": i.source}
                    for i in items
                ]
            },
        )

    @staticmethod
    def polarity(title: str) -> float:
        return _polarity(title)

    @staticmethod
    def recent(items: list[NewsItem], window_hours: float = 24.0) -> list[NewsItem]:
        cutoff = utc_now() - timedelta(hours=window_hours)
        return [i for i in items if i.published >= cutoff]
