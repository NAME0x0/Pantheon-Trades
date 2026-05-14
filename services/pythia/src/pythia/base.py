from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from pydantic import BaseModel

from pantheon_core.schema import utc_now


class SourceSnapshot(BaseModel):
    source: str
    fetched_at: datetime
    data: dict


class DataSource(ABC):
    """Base class for all Pythia data sources."""

    name: str
    max_staleness_seconds: int = 300

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._last_fetch: datetime | None = None
        self._cached: SourceSnapshot | None = None

    @abstractmethod
    async def fetch(self) -> SourceSnapshot:
        """Fetch fresh data from source."""

    async def get(self, force: bool = False) -> SourceSnapshot:
        now = utc_now()
        if not force and self._cached and self._last_fetch:
            age = (now - self._last_fetch).total_seconds()
            if age < self.max_staleness_seconds:
                return self._cached
        snapshot = await self.fetch()
        self._cached = snapshot
        self._last_fetch = now
        return snapshot

    def staleness_seconds(self) -> int:
        if self._last_fetch is None:
            return 999999
        return int((utc_now() - self._last_fetch).total_seconds())
