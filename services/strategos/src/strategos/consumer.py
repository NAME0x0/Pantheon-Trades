"""Strategos consumer — reads approval tokens and routes them.

Pairs each ``ApprovalToken`` on the ``areopagus:approvals`` stream with the
matching cached Thesis (so we know direction + edge for sizing), pulls a
fresh mid price + depth from Polymarket (live mode) or a stubbed depth
(paper mode), and dispatches via the ``Strategos`` router. Resulting
Trade records go to the ``strategos:trades`` stream so Argos can pick them
up and start monitoring exits.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import ApprovalToken, Thesis

from strategos.live import LiveExecutor
from strategos.paper import PaperBook
from strategos.polymarket_clob import PolymarketClobClient
from strategos.router import Strategos

log = structlog.get_logger("strategos.consumer")

APPROVALS_STREAM = "areopagus:approvals"
TRADES_STREAM = "strategos:trades"
CONSUMER_GROUP = "strategos"
DEFAULT_CONSUMER_NAME = os.environ.get("HOSTNAME", "strategos-1")
BLOCK_MS = 5_000
BATCH = 5
DEFAULT_PORTFOLIO = float(os.environ.get("PORTFOLIO_USDC", "10000"))
DEFAULT_DEPTH = 50_000.0


async def _ensure_group(redis: aioredis.Redis) -> None:
    try:
        await redis.xgroup_create(
            name=APPROVALS_STREAM, groupname=CONSUMER_GROUP, id="$", mkstream=True
        )
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _fetch_thesis(redis: aioredis.Redis, thesis_id: str) -> Thesis | None:
    raw = await redis.get(f"boule:thesis:{thesis_id}")
    if not raw:
        return None
    try:
        return Thesis.model_validate_json(raw)
    except Exception as e:  # noqa: BLE001
        log.warning("strategos.consumer.bad_thesis_cache", error=str(e))
        return None


async def _fetch_book(
    http: httpx.AsyncClient, market_id: str
) -> tuple[float, float, str | None, str | None]:
    """Pull Polymarket market + book; return (mid, depth, yes_token, no_token).

    Falls back to a synthetic 50/50 mid + default depth on any failure so
    paper mode keeps moving.
    """
    try:
        resp = await http.get(
            f"https://clob.polymarket.com/markets/{market_id}", timeout=10.0
        )
        resp.raise_for_status()
        market = resp.json()
    except Exception:
        return 0.5, DEFAULT_DEPTH, None, None

    yes_token = no_token = None
    tokens = market.get("tokens") or []
    for t in tokens:
        outcome = (t.get("outcome") or "").upper()
        if outcome.startswith("Y"):
            yes_token = t.get("token_id") or t.get("tokenId")
        elif outcome.startswith("N"):
            no_token = t.get("token_id") or t.get("tokenId")

    if yes_token:
        try:
            book_resp = await http.get(
                "https://clob.polymarket.com/book",
                params={"token_id": yes_token},
                timeout=10.0,
            )
            book_resp.raise_for_status()
            book = book_resp.json()
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            best_bid = float(bids[0]["price"]) if bids else 0.0
            best_ask = float(asks[0]["price"]) if asks else 1.0
            mid = (best_bid + best_ask) / 2.0
            depth = sum(float(a["price"]) * float(a["size"]) for a in asks[:5]) or DEFAULT_DEPTH
            return mid, depth, yes_token, no_token
        except Exception:
            pass

    mid = float(market.get("last_trade_price") or 0.5)
    return mid, DEFAULT_DEPTH, yes_token, no_token


async def _build_router() -> Strategos:
    paper = PaperBook(portfolio_usdc=DEFAULT_PORTFOLIO)
    live: LiveExecutor | None = None
    mode = os.environ.get("EXECUTION_MODE", "paper")
    if mode in ("live", "auto"):
        try:
            clob = PolymarketClobClient()
            live = LiveExecutor(clob=clob, portfolio_usdc=DEFAULT_PORTFOLIO)
        except Exception as e:  # noqa: BLE001
            log.warning("strategos.consumer.live_disabled", error=str(e))
    return Strategos(paper=paper, live=live, mode=mode)  # type: ignore[arg-type]


async def _process(
    redis: aioredis.Redis,
    http: httpx.AsyncClient,
    router: Strategos,
    raw_token: dict[str, Any],
) -> None:
    try:
        token = ApprovalToken.model_validate(raw_token)
    except Exception as e:  # noqa: BLE001
        log.warning("strategos.consumer.bad_token", error=str(e))
        return

    if token.decision not in ("APPROVED", "RESIZED"):
        return

    thesis = await _fetch_thesis(redis, token.thesis_id)
    if thesis is None:
        log.warning("strategos.consumer.thesis_missing", thesis_id=token.thesis_id)
        return

    mid, depth, yes_token, no_token = await _fetch_book(http, thesis.market_id)
    trade = await router.execute(
        token=token,
        thesis=thesis,
        mid_price=mid,
        depth_usdc=depth,
        yes_token_id=yes_token,
        no_token_id=no_token,
    )
    await redis.xadd(
        TRADES_STREAM,
        {"data": trade.model_dump_json()},
        maxlen=50_000,
        approximate=True,
    )
    await redis.setex(
        f"strategos:trade:{trade.trade_id}",
        7 * 86_400,
        trade.model_dump_json(),
    )
    log.info(
        "strategos.routed",
        thesis_id=thesis.thesis_id,
        trade_id=trade.trade_id,
        status=trade.status,
        direction=trade.direction,
        mid=mid,
    )


async def consume_forever(
    redis_url: str | None = None,
    consumer_name: str = DEFAULT_CONSUMER_NAME,
) -> None:
    redis = await aioredis.from_url(
        redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    http = httpx.AsyncClient(timeout=15.0)
    router = await _build_router()

    await _ensure_group(redis)
    log.info("strategos.consumer.start", consumer=consumer_name, mode=router.mode)

    try:
        while True:
            response = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={APPROVALS_STREAM: ">"},
                count=BATCH,
                block=BLOCK_MS,
            )
            if not response:
                continue
            for _stream, entries in response:
                for entry_id, fields in entries:
                    payload = fields.get("data") if isinstance(fields, dict) else None
                    if not payload:
                        await redis.xack(APPROVALS_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        raw_token = json.loads(payload)
                    except (ValueError, json.JSONDecodeError):
                        await redis.xack(APPROVALS_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        await _process(redis, http, router, raw_token)
                    except Exception as e:  # noqa: BLE001
                        log.exception(
                            "strategos.consumer.process_failed",
                            entry_id=entry_id,
                            error=str(e),
                        )
                        continue
                    await redis.xack(APPROVALS_STREAM, CONSUMER_GROUP, entry_id)
    finally:
        await http.aclose()
        await redis.aclose()
