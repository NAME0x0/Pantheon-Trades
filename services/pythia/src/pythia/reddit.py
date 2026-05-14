"""Reddit social sentiment via PRAW (read-only).

PRAW is synchronous; we run it in a thread so the async event loop stays
responsive. The output mirrors NewsSource so Apollo can pipe both into the
same sentiment aggregator.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot
from pythia.news import _polarity

DEFAULT_SUBREDDITS = (
    "CryptoCurrency",
    "wallstreetbets",
    "Bitcoin",
    "ethereum",
    "Polymarket",
)


@dataclass(frozen=True)
class RedditPost:
    title: str
    score: int
    num_comments: int
    subreddit: str
    polarity: float


def _build_client():
    """Lazily import PRAW so unit tests don't require the dependency."""
    import praw  # type: ignore[import-not-found]

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "pantheon-pythia/0.1"),
        ratelimit_seconds=600,
    )


class RedditSource(DataSource):
    name = "reddit"
    max_staleness_seconds = 900

    def __init__(
        self,
        client: httpx.AsyncClient,
        subreddits: tuple[str, ...] = DEFAULT_SUBREDDITS,
        limit_per_sub: int = 25,
    ) -> None:
        super().__init__(client)
        self._subreddits = subreddits
        self._limit = limit_per_sub

    def _fetch_sync(self) -> list[RedditPost]:
        reddit = _build_client()
        out: list[RedditPost] = []
        for sub in self._subreddits:
            try:
                for post in reddit.subreddit(sub).hot(limit=self._limit):
                    title = post.title or ""
                    out.append(
                        RedditPost(
                            title=title,
                            score=getattr(post, "score", 0) or 0,
                            num_comments=getattr(post, "num_comments", 0) or 0,
                            subreddit=sub,
                            polarity=_polarity(title),
                        )
                    )
            except Exception:
                continue
        return out

    async def fetch(self) -> SourceSnapshot:
        posts = await asyncio.to_thread(self._fetch_sync)
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={
                "posts": [
                    {
                        "title": p.title,
                        "score": p.score,
                        "num_comments": p.num_comments,
                        "subreddit": p.subreddit,
                        "polarity": p.polarity,
                    }
                    for p in posts
                ]
            },
        )
