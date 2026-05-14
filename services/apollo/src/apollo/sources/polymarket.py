"""Translate Polymarket CLOB market payloads into Apollo MarketSnapshots.

Pythia's ``PolymarketSource`` returns raw JSON. Apollo's ``score_market``
wants a normalised ``MarketSnapshot`` with computed deltas. This module is
the single place where Polymarket field names live in Apollo — every other
module talks in ``MarketSnapshot`` terms.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from pantheon_core.schema import utc_now

from apollo.features.catalyst import CatalystEvent
from apollo.features.sentiment import SentimentSample
from apollo.scorer import MarketSnapshot


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "crypto": ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "doge", "crypto"),
    "politics": ("election", "president", "senate", "house", "congress", "policy", "trump", "biden"),
    "sports": ("nba", "nfl", "mlb", "soccer", "football", "basketball", "world cup"),
    "science": ("vaccine", "cern", "nasa", "spacex", "launch", "discovery", "physics"),
}


def _infer_category(question: str) -> Literal["crypto", "politics", "sports", "science", "other"]:
    q = (question or "").lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in kws):
            return cat  # type: ignore[return-value]
    return "other"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        # Polymarket exposes ISO-8601 like "2026-12-31T23:59:59Z".
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _days_to(resolution: datetime | None) -> float | None:
    if resolution is None:
        return None
    delta = resolution - utc_now()
    return delta.total_seconds() / 86400.0


@dataclass(frozen=True)
class _OrderBookSummary:
    bid: float
    ask: float
    spread: float


def _summarise_orderbook(book: dict[str, Any]) -> _OrderBookSummary:
    bids = book.get("bids", []) or []
    asks = book.get("asks", []) or []
    best_bid = _safe_float(bids[0].get("price"), 0.0) if bids else 0.0
    best_ask = _safe_float(asks[0].get("price"), 1.0) if asks else 1.0
    spread = max(0.0, best_ask - best_bid)
    return _OrderBookSummary(bid=best_bid, ask=best_ask, spread=spread)


def snapshot_from_market_payload(
    market: dict[str, Any],
    *,
    book: dict[str, Any] | None = None,
    price_history: list[float] | None = None,
    catalysts: list[CatalystEvent] | None = None,
    sentiment_samples: list[SentimentSample] | None = None,
    open_position_correlations: list[float] | None = None,
    sentiment_adjustment: float = 0.0,
    trend_adjustment: float = 0.0,
    catalyst_adjustment: float = 0.0,
    calibration_factor: float = 1.0,
    source_trust_score: float = 1.0,
    extra_sources: list[str] | None = None,
) -> MarketSnapshot:
    """Build a ``MarketSnapshot`` from a single Polymarket market record.

    ``market`` is the dict returned by ``GET /markets/{condition_id}``.
    ``book`` is the matching ``GET /book`` response; if omitted we infer
    bid/ask from the market record's last_trade_price.
    """
    question = market.get("question") or market.get("title") or ""
    market_id = (
        market.get("condition_id")
        or market.get("conditionId")
        or market.get("id")
        or ""
    )
    category = _infer_category(question)

    if book:
        ob = _summarise_orderbook(book)
        bid, ask, spread = ob.bid, ob.ask, ob.spread
        mid = (bid + ask) / 2.0
    else:
        mid = _safe_float(market.get("last_trade_price") or market.get("lastTradePrice"), 0.5)
        spread = _safe_float(market.get("spread"), 0.04)
        bid = max(0.0, mid - spread / 2.0)
        ask = min(1.0, mid + spread / 2.0)

    volume_24h = _safe_float(
        market.get("volume24hr") or market.get("volume_24hr") or market.get("volume"),
        0.0,
    )
    open_interest = _safe_float(
        market.get("open_interest") or market.get("openInterest"),
        0.0,
    )

    history = price_history or []
    if history:
        recent_avg = sum(history[-7:]) / max(len(history[-7:]), 1)
        std_24h = (sum((p - recent_avg) ** 2 for p in history[-24:]) / max(len(history[-24:]), 1)) ** 0.5
    else:
        std_24h = 0.0
        recent_avg = mid

    resolution = _parse_iso(market.get("end_date_iso") or market.get("endDate"))
    days_to = _days_to(resolution)

    sources = ["polymarket"]
    if extra_sources:
        sources.extend(extra_sources)

    return MarketSnapshot(
        market_id=str(market_id),
        question=question,
        category=category,
        market_probability=max(0.001, min(0.999, mid)),
        bid=bid,
        ask=ask,
        volume_24h=volume_24h,
        open_interest=open_interest,
        price_history=history,
        price_std_24h=std_24h,
        price_mean=recent_avg or mid,
        catalysts=catalysts or [],
        sentiment_samples=sentiment_samples or [],
        open_position_correlations=open_position_correlations or [],
        data_sources=sources,
        snapshot_at=utc_now(),
        staleness_seconds=0,
        source_trust_score=source_trust_score,
        resolution_date=resolution,
        days_to_resolution=days_to,
        sentiment_adjustment=sentiment_adjustment,
        trend_adjustment=trend_adjustment,
        catalyst_adjustment=catalyst_adjustment,
        calibration_factor=calibration_factor,
    )


class PolymarketSnapshotBuilder:
    """Stateful builder that combines market + book + recent prices from Pythia."""

    def __init__(self, *, source_trust_score: float = 1.0) -> None:
        self._trust = source_trust_score

    def build(
        self,
        market: dict[str, Any],
        *,
        book: dict[str, Any] | None = None,
        price_history: list[float] | None = None,
    ) -> MarketSnapshot:
        return snapshot_from_market_payload(
            market,
            book=book,
            price_history=price_history,
            source_trust_score=self._trust,
        )
