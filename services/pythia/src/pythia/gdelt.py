"""GDELT 2.0 Document API — real-time global event signal.

GDELT (Global Database of Events, Language, and Tone) catalogues news
events from print + broadcast + web across 100+ languages with 15-min
update cadence ([gdeltproject.org](https://www.gdeltproject.org/)).
The 2.0 Document API exposes filtered article timelines with no key
required — free and rate-limited at the IP level (a few hundred calls
per minute is fine).

Three use cases we care about:

  1. ``article_timeline(query, hours=24)`` — counts of articles
     matching a free-text or themed query over the past N hours.
     A leading indicator for any market where the volume of coverage
     should track resolution probability.

  2. ``tone_timeline(query, hours=24)`` — average GDELT tone across
     matched articles. Tone is GDELT's news-sentiment score in
     ``[-100, +100]``. Useful as input to Cassandra's tail-risk reads.

  3. ``geopolitical_risk(country_code, hours=72)`` — composite score
     combining tone + article volume + theme keywords (PROTEST,
     MILITARY_CONFLICT, etc.) for a given country. Used by Apollo's
     ``geopolitical_risk_score`` feature on world-event markets.

Why this matters: a 2025 arxiv paper applied GDELT + FinBERT to FX
trading and reported out-of-sample Sharpe 5.87 on EUR/USD and 4.65 on
USD/JPY ([arxiv.org/abs/2505.16136](https://arxiv.org/abs/2505.16136)).
The signal exists in public data; the alpha is in the *extraction*.
This module gives the wiring; the extraction is up to the operator.

For very-large historical pulls, use the BigQuery dataset (1TB/month
free on Google Cloud) instead — see docs/FEES_AND_EDGE.md for the
pointer.

API reference: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

# DOC API base. JSON mode is what we want for programmatic consumption.
DOC_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT timeline modes we support. ToneList + ArtList are the two
# cheapest signals to derive a "is this market moving?" feature from.
TimelineMode = Literal["timelinevolinfo", "timelinetone", "timelinevol"]


def _fmt_gdelt_dt(dt: datetime) -> str:
    """GDELT expects YYYYMMDDhhmmss in UTC."""
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


class GdeltSource(DataSource):
    """Free, no-key GDELT 2.0 Document API client.

    Returns SourceSnapshot.data shaped as
    ``{"query": ..., "mode": ..., "timeline": [{"datetime": ..., "value": ...}, ...]}``.
    """

    name = "gdelt"
    # 15 min API cadence; cache to match. Operator can override per
    # instance if they hit GDELT harder elsewhere in the pipeline.
    max_staleness_seconds = 900

    DEFAULT_QUERY = "elections OR conflict OR crisis"

    async def fetch(self) -> SourceSnapshot:
        """Pull a 24-hour article-volume timeline for the default query.

        Use ``timeline()`` directly for any non-default query — this
        ``fetch`` implementation exists only to satisfy DataSource's
        abstract contract and to give callers a "did the connector
        actually work?" smoke check.
        """
        out = await self.timeline(self.DEFAULT_QUERY, mode="timelinevol", hours=24)
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data=out,
        )

    async def timeline(
        self,
        query: str,
        *,
        mode: TimelineMode = "timelinevol",
        hours: int = 24,
        max_records: int = 200,
    ) -> dict:
        """Generic timeline fetch. Returns a parsed JSON dict.

        Args:
            query: GDELT DOC query string. Themes can be specified as
                ``theme:PROTEST`` or ``sourcecountry:US`` per the DOC
                API syntax. Free text works too.
            mode: GDELT timeline mode. ``timelinevol`` returns article
                counts per 15-min bucket; ``timelinetone`` returns
                average article tone; ``timelinevolinfo`` is both.
            hours: lookback window. GDELT supports 1h–24h for live;
                BigQuery for longer.
            max_records: bound on records returned.
        """
        now = utc_now()
        start = now - timedelta(hours=hours)
        params = {
            "query": query,
            "mode": mode,
            "format": "json",
            "startdatetime": _fmt_gdelt_dt(start),
            "enddatetime": _fmt_gdelt_dt(now),
            "maxrecords": str(max_records),
        }
        resp = await self._client.get(DOC_API_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        body = resp.json()
        # The DOC API embeds timeline values under different keys
        # depending on mode — normalise to a single "timeline" list.
        series = body.get("timeline") or body.get("timelinevol") or body.get("timelinetone") or []
        return {"query": query, "mode": mode, "timeline": series, "raw": body}

    async def article_count(self, query: str, *, hours: int = 24) -> int:
        """Total article count over the window for ``query``.

        Cheap one-shot for "is this question getting attention?"
        features.
        """
        out = await self.timeline(query, mode="timelinevol", hours=hours)
        return sum(int(p.get("value", 0)) for p in out["timeline"])

    async def average_tone(self, query: str, *, hours: int = 24) -> float | None:
        """Article-volume-weighted average tone for ``query`` over the
        window. Returns ``None`` if no articles matched.

        Tone is GDELT's news-sentiment score in approximately
        [-100, +100]. Negative numbers indicate distressed coverage.
        """
        info = await self.timeline(query, mode="timelinevolinfo", hours=hours)
        series = info["timeline"]
        if not series:
            return None
        weighted = 0.0
        total = 0
        for p in series:
            v = int(p.get("value", 0))
            t = float(p.get("tone", 0.0))
            weighted += v * t
            total += v
        return weighted / total if total > 0 else None

    async def geopolitical_risk(
        self,
        country_code: str,
        *,
        hours: int = 72,
    ) -> dict:
        """Composite risk score for a country over ``hours`` of coverage.

        Returns ``{"country": ..., "article_count": int, "tone": float
        | None, "risk_score": float}`` where ``risk_score`` is in
        ``[0, 1]`` — high values mean lots of distressed coverage,
        low values mean either no coverage or upbeat coverage.

        This is a deliberately simple combination of two GDELT signals.
        Operators wanting more should write their own scorer in
        ``apollo.features``.
        """
        cc = country_code.upper()
        # GDELT's `sourcecountry:` filter + a coarse "risk" lexicon.
        query = (
            f"sourcecountry:{cc} AND "
            "(protest OR conflict OR crisis OR sanction OR coup OR election)"
        )
        n = await self.article_count(query, hours=hours)
        tone = await self.average_tone(query, hours=hours)
        # Normalise:
        # - article count contribution: 1 - exp(-n / 50). Hits 0.86 at n=100.
        # - tone contribution: -tone / 10 clipped to [0, 1]. Negative
        #   tone (-10 or worse) saturates the score.
        import math

        vol_part = 1.0 - math.exp(-max(0, n) / 50.0)
        if tone is None:
            tone_part = 0.5  # no data = neutral prior
        else:
            tone_part = max(0.0, min(1.0, -tone / 10.0))
        risk = 0.5 * vol_part + 0.5 * tone_part
        return {
            "country": cc,
            "article_count": n,
            "tone": tone,
            "risk_score": round(risk, 4),
        }
