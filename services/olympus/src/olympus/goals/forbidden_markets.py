"""Forbidden markets — explicit ban list checked before deliberation.

Operators can blacklist markets (regulatory, legal, ethical) so Apollo
never even hands them to Boule. The registry is keyed by ``market_id``
or by a substring match on the question text.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ForbiddenMarketsRegistry:
    market_ids: set[str] = field(default_factory=set)
    question_substrings: set[str] = field(default_factory=set)

    def add_market(self, market_id: str) -> None:
        self.market_ids.add(market_id)

    def add_substring(self, substring: str) -> None:
        if not substring:
            return
        self.question_substrings.add(substring.lower())

    def is_forbidden(self, *, market_id: str = "", question: str = "") -> bool:
        if market_id and market_id in self.market_ids:
            return True
        q = (question or "").lower()
        return any(token in q for token in self.question_substrings)


def is_forbidden(
    registry: ForbiddenMarketsRegistry, *, market_id: str = "", question: str = ""
) -> bool:
    return registry.is_forbidden(market_id=market_id, question=question)
