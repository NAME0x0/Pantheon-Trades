"""Wikipedia pageviews — investor-attention proxy data source.

Wikimedia exposes a free, no-auth, hourly pageviews REST API
(``wikimedia.org/api/rest_v1/metrics/pageviews``). For prediction
markets whose underlying entity has a Wikipedia article (elections,
court rulings, sports finals, central-bank decisions, technology
launches), spikes in pageviews are a documented leading indicator of
subsequent market moves.

See ``docs/FEES_AND_EDGE.md`` §3b for the academic references and
mechanism.

This module returns daily or hourly pageview counts and a single
attention-velocity z-score over a rolling window.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
Granularity = Literal["daily", "hourly"]


def _fmt_wiki_date(dt: datetime, granularity: Granularity) -> str:
    """Wikimedia expects YYYYMMDD for daily, YYYYMMDDHH for hourly, UTC."""
    dt = dt.astimezone(timezone.utc)
    if granularity == "hourly":
        return dt.strftime("%Y%m%d%H")
    return dt.strftime("%Y%m%d")


class WikipediaSource(DataSource):
    """Free Wikipedia pageviews API. No key, no auth, ~100 req/s limit."""

    name = "wikipedia"
    # Daily granularity max — cache for 6h. Hourly callers should
    # override per-call.
    max_staleness_seconds = 6 * 3600

    DEFAULT_PROJECT = "en.wikipedia"
    DEFAULT_ACCESS = "all-access"
    DEFAULT_AGENT = "user"  # excludes spider / bot traffic

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: pageviews on Bitcoin for the last 30 days."""
        out = await self.daily_views(article="Bitcoin", days=30)
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data=out)

    async def daily_views(self, article: str, *, days: int = 30) -> dict:
        """Return daily pageview counts for ``article`` over the last
        ``days`` days. Article title is the URL-form (underscores, not
        spaces). Case-sensitive.
        """
        end = utc_now() - timedelta(days=1)  # Wikimedia lags ~1 day
        start = end - timedelta(days=days)
        return await self._fetch_range(article, start, end, "daily")

    async def hourly_views(self, article: str, *, hours: int = 168) -> dict:
        """Hourly pageviews for the last ``hours`` hours."""
        end = utc_now() - timedelta(hours=2)  # ~2h lag for hourly
        start = end - timedelta(hours=hours)
        return await self._fetch_range(article, start, end, "hourly")

    async def _fetch_range(
        self,
        article: str,
        start: datetime,
        end: datetime,
        granularity: Granularity,
    ) -> dict:
        # URL-escape the article name. Wikimedia accepts double-encoded
        # spaces as %20 only when not pre-underscored, but for safety
        # we keep this minimal.
        article_clean = article.strip().replace(" ", "_")
        path = (
            f"/per-article/{self.DEFAULT_PROJECT}/{self.DEFAULT_ACCESS}/"
            f"{self.DEFAULT_AGENT}/{article_clean}/{granularity}/"
            f"{_fmt_wiki_date(start, granularity)}/{_fmt_wiki_date(end, granularity)}"
        )
        url = f"{API_BASE}{path}"
        resp = await self._client.get(url, timeout=15.0)
        resp.raise_for_status()
        body = resp.json()
        items = body.get("items", [])
        # Normalise to a simple list of {timestamp, views}
        timeline = [
            {"timestamp": it.get("timestamp"), "views": int(it.get("views", 0))}
            for it in items
        ]
        return {
            "article": article_clean,
            "project": self.DEFAULT_PROJECT,
            "granularity": granularity,
            "timeline": timeline,
        }

    async def attention_velocity_z(
        self,
        article: str,
        *,
        window_days: int = 30,
        recent_days: int = 3,
    ) -> float | None:
        """Z-score of the recent ``recent_days`` mean vs the ``window_days``
        baseline. High positive z → article suddenly interesting.

        Returns ``None`` if Wikipedia has no data for the article over
        the requested window (e.g. brand-new entity).
        """
        out = await self.daily_views(article, days=window_days)
        series = [p["views"] for p in out["timeline"]]
        if len(series) < recent_days + 1:
            return None
        baseline = series[:-recent_days]
        recent = series[-recent_days:]
        if not baseline or not recent:
            return None
        mu = sum(baseline) / len(baseline)
        var = sum((x - mu) ** 2 for x in baseline) / max(1, len(baseline) - 1)
        sd = var ** 0.5
        if sd <= 0:
            return None
        recent_mean = sum(recent) / len(recent)
        return (recent_mean - mu) / sd
