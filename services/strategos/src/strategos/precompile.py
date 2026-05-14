"""Precompiled order templates — keep frequent build paths warm.

For markets where Strategos repeatedly executes the same token pair,
cache the ABI-encoded order template so a fresh ApprovalToken only
substitutes the mutable fields (price, size). Reduces signing-path
latency for high-frequency markets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrderTemplate:
    market_id: str
    yes_token_id: str
    no_token_id: str


@dataclass
class TemplateCache:
    _by_market: dict[str, OrderTemplate] = field(default_factory=dict)

    def put(self, market_id: str, yes_token_id: str, no_token_id: str) -> None:
        self._by_market[market_id] = OrderTemplate(
            market_id=market_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
        )

    def get(self, market_id: str) -> OrderTemplate | None:
        return self._by_market.get(market_id)

    def warm(self, templates: list[OrderTemplate]) -> None:
        for t in templates:
            self._by_market[t.market_id] = t
