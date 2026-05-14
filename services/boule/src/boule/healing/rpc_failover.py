"""RPC failover — rotate between Arc endpoints on health failure."""

from __future__ import annotations

from collections.abc import Iterable


DEFAULT_ENDPOINTS = (
    "https://rpc.testnet.arc.network",
    "https://arc-testnet.drpc.org",
)


class RpcFailover:
    def __init__(self, endpoints: Iterable[str] = DEFAULT_ENDPOINTS) -> None:
        self._endpoints = list(endpoints)
        if not self._endpoints:
            raise ValueError("at least one endpoint required")
        self._index = 0

    @property
    def current(self) -> str:
        return self._endpoints[self._index]

    def rotate(self) -> str:
        self._index = (self._index + 1) % len(self._endpoints)
        return self.current

    def reset(self) -> None:
        self._index = 0
