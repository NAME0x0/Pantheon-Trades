"""Order-book utilities — depth, mid, and spread computation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Level:
    price: float
    size: float


@dataclass(frozen=True)
class Book:
    bids: list[Level]
    asks: list[Level]

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 1.0

    @property
    def mid(self) -> float:
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float:
        return max(0.0, self.best_ask - self.best_bid)

    def depth_usdc(self, levels: int = 5, side: str = "asks") -> float:
        layers = (self.asks if side == "asks" else self.bids)[:levels]
        return sum(layer.price * layer.size for layer in layers)


def parse_book(payload: dict) -> Book:
    """Parse a Polymarket CLOB ``/book`` response into a typed Book."""
    bids = [
        Level(price=float(b["price"]), size=float(b["size"]))
        for b in payload.get("bids", [])
    ]
    asks = [
        Level(price=float(a["price"]), size=float(a["size"]))
        for a in payload.get("asks", [])
    ]
    bids.sort(key=lambda lvl: lvl.price, reverse=True)
    asks.sort(key=lambda lvl: lvl.price)
    return Book(bids=bids, asks=asks)
