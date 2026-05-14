"""Paper arena — competitive sandbox where multiple strategies trade in parallel.

Each arena holds a roster of strategy entries, each with its own paper book
and its own deliberate function. After a tick the arena ranks entries by
running PnL so Moirai can pick promotion candidates.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from pantheon_core.schema import Signal, Thesis

DeliberateFn = Callable[[Signal], Awaitable[Thesis]]


@dataclass
class ArenaEntry:
    strategy_id: str
    deliberate: DeliberateFn
    paper_book: object  # avoid hard import of strategos.paper.PaperBook
    realised_pnl_usdc: float = 0.0
    n_trades: int = 0
    n_wins: int = 0


@dataclass
class PaperArena:
    entries: list[ArenaEntry] = field(default_factory=list)

    def add(self, entry: ArenaEntry) -> None:
        self.entries.append(entry)

    async def tick(self, signal: Signal, court, resolve) -> None:
        from pantheon_core.schema import ApprovalToken, RejectionRecord  # local import
        for entry in self.entries:
            thesis = await entry.deliberate(signal)
            verdict = court.evaluate_thesis(thesis, signal)
            if isinstance(verdict, RejectionRecord):
                continue
            assert isinstance(verdict, ApprovalToken)
            trade = entry.paper_book.execute(  # type: ignore[attr-defined]
                verdict, thesis,
                mid_price=signal.market_probability,
                depth_usdc=signal.volume_24h or 50_000.0,
            )
            entry.n_trades += 1
            resolution = resolve(signal.market_id, signal.resolution_date)
            pnl = entry.paper_book.settle(  # type: ignore[attr-defined]
                trade.trade_id, resolution_yes_price=resolution
            )
            entry.realised_pnl_usdc += pnl
            if pnl > 0:
                entry.n_wins += 1

    def leaderboard(self) -> list[ArenaEntry]:
        return sorted(self.entries, key=lambda e: -e.realised_pnl_usdc)
