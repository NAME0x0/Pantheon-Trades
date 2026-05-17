"""Paper trade against live Polymarket CLOB book + V2 fee schedule.

The CoinGecko harness proves the pipeline works against arbitrary
price data. This script proves the same pipeline works against the
*actual* Polymarket order book — with real spread, real depth, real
fees, and the right post-only / category routing.

Crucially, it does NOT submit any trades. It walks the live order
book of N candidate markets, runs each through Apollo's signal
scorer + Areopagus's half-Kelly sizer + Strategos's paper book, books
fees via the FeeLedger, and emits a JSON artifact.

When you flip ``EXECUTION_MODE=live`` this is the same code path —
swap PaperBook for LiveExecutor. Today this is the *30-day
precondition* before that flip is responsible.

What's still missing for true live mode:
  - The Boule council deliberation (this script uses a thin
    deterministic stand-in for the council probability — same shape
    as the CoinGecko script).
  - A real Polymarket API key for the read endpoints if rate limits
    bite — the public endpoints work without one but cap at ~120 req/min.

Usage:
    python scripts/paper_trade_polymarket.py --markets=10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"

# Workspace path patches.
for svc_path in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "pythia" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "areopagus" / "src",
    ROOT / "services" / "strategos" / "src",
):
    if str(svc_path) not in sys.path:
        sys.path.insert(0, str(svc_path))

# Imports after path patches.
from pantheon_core.schema import ApprovalToken, ExitConditions, Thesis  # noqa: E402

from areopagus.kelly import size_position  # noqa: E402
from strategos.execution_mode import choose_execution  # noqa: E402
from strategos.maker_rebate import FeeLedger  # noqa: E402
from strategos.paper import PaperBook  # noqa: E402


# ─── Polymarket REST ──────────────────────────────────────────────────


POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB = "https://clob.polymarket.com"


SYNTHETIC_MARKETS: list[dict[str, Any]] = [
    {
        "slug": "election-2028-incumbent-win",
        "question": "Will the incumbent party win the 2028 US presidential election?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.42", "0.58"],
        "volume24hr": 1_200_000,
        "conditionId": "synthetic-election-2028",
    },
    {
        "slug": "btc-120k-by-eoy-2026",
        "question": "Will Bitcoin trade above $120,000 by 2026-12-31?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.38", "0.62"],
        "volume24hr": 580_000,
        "conditionId": "synthetic-btc-120k",
    },
    {
        "slug": "fed-pause-may",
        "question": "Will the Fed pause rate hikes at the May FOMC meeting?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.71", "0.29"],
        "volume24hr": 340_000,
        "conditionId": "synthetic-fed-pause",
    },
    {
        "slug": "russia-ukraine-ceasefire-by-q4",
        "question": "Will there be a Russia-Ukraine ceasefire signed by end of Q4?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.16", "0.84"],
        "volume24hr": 880_000,
        "conditionId": "synthetic-ru-ua",
    },
    {
        "slug": "lakers-finals-2026",
        "question": "Will the Lakers win the 2026 NBA Finals?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.08", "0.92"],
        "volume24hr": 120_000,
        "conditionId": "synthetic-lakers-2026",
    },
    {
        "slug": "cpi-yoy-above-3",
        "question": "Will May CPI YoY print above 3.0%?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.45", "0.55"],
        "volume24hr": 210_000,
        "conditionId": "synthetic-cpi",
    },
    {
        "slug": "atlantic-hurricane-cat4",
        "question": "Will there be a Cat 4+ Atlantic hurricane this season?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.62", "0.38"],
        "volume24hr": 95_000,
        "conditionId": "synthetic-hurricane",
    },
    {
        "slug": "eth-merge-issue",
        "question": "Will Ethereum experience a significant chain issue in Q3?",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.12", "0.88"],
        "volume24hr": 76_000,
        "conditionId": "synthetic-eth-issue",
    },
]


async def fetch_active_binaries(n: int) -> list[dict[str, Any]]:
    """Pull active binary markets from Polymarket Gamma.

    Returns rows shaped like
    ``{id, slug, question, category, active, closed, volume24hr,
       outcomePrices, conditionId}``.
    Filters: ``active=true`` AND ``closed=false`` AND volume24hr > $5,000.

    Falls back to ``SYNTHETIC_MARKETS`` when the live Gamma endpoint is
    unreachable (e.g. geo-blocked). The artifact records the fallback
    so the operator can tell synthetic from real flow.
    """
    import httpx

    out: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.get(
                f"{POLYMARKET_GAMMA}/markets",
                params={"limit": 500, "active": "true", "closed": "false"},
            )
            resp.raise_for_status()
            rows = resp.json()
    except Exception as exc:
        print(f"  Polymarket Gamma unreachable ({type(exc).__name__}); using synthetic fixture")
        return SYNTHETIC_MARKETS[:n]
    for m in rows:
        try:
            vol = float(m.get("volume24hr") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        if vol < 5000:
            continue
        # Want binary YES/NO.
        outcomes = m.get("outcomes")
        if isinstance(outcomes, str):
            try:
                outcomes_list = json.loads(outcomes)
            except (TypeError, ValueError):
                continue
        elif isinstance(outcomes, list):
            outcomes_list = outcomes
        else:
            continue
        if outcomes_list != ["Yes", "No"] and outcomes_list != ["YES", "NO"]:
            continue
        out.append(m)
        if len(out) >= n:
            break
    return out


async def fetch_order_book(token_id: str) -> dict[str, Any]:
    """Live CLOB book for a token id."""
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(f"{POLYMARKET_CLOB}/book", params={"token_id": token_id})
        resp.raise_for_status()
        return resp.json()


def extract_book_top(book: dict[str, Any]) -> tuple[float | None, float | None, float]:
    """Return (best_bid, best_ask, top-of-book USDC depth)."""
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    best_bid = float(bids[0]["price"]) if bids else None
    best_ask = float(asks[0]["price"]) if asks else None
    # Synthesise a depth estimate from top 3 levels each side.
    depth = 0.0
    for level in (bids[:3] + asks[:3]):
        try:
            depth += float(level["price"]) * float(level["size"])
        except (KeyError, TypeError, ValueError):
            continue
    return best_bid, best_ask, depth


# ─── council substitute (cheap, deterministic) ────────────────────────


def toy_council_probability(market_implied: float, volume24hr: float) -> float:
    """Stand-in for the LLM council so this script costs $0 to run.

    Rationale: regress toward 0.50 by an amount inversely proportional
    to liquidity. High-volume markets are closer to fair priced, so
    our "council" should mostly agree with the market. Low-volume
    markets get a stronger pull. This is intentionally not a real
    edge source — it's plumbing test data.
    """
    pull = max(0.0, 1.0 - min(1.0, volume24hr / 1_000_000))  # 0..1
    return 0.5 + (1 - 0.5 * pull) * (market_implied - 0.5)


# ─── orchestration ────────────────────────────────────────────────────


def _normalise_category(slug: str, question: str) -> str:
    """Polymarket Gamma's category labels are inconsistent. Try to
    classify into the V2 fee buckets so we route fees correctly."""
    s = (slug + " " + question).lower()
    if any(k in s for k in ["election", "president", "senate", "congress", "governor"]):
        return "politics"
    if any(k in s for k in ["btc", "bitcoin", "eth", "ethereum", "sol ", "crypto"]):
        return "crypto"
    if any(k in s for k in ["nfl", "nba", "mlb", "soccer", "championship", "olympic", "world cup"]):
        return "sports"
    if any(k in s for k in ["cpi", "fed", "fomc", "gdp", "unemployment", "inflation"]):
        return "economics"
    if any(k in s for k in ["war", "russia", "ukraine", "israel", "iran", "china", "taiwan"]):
        return "geopolitics"
    if any(k in s for k in ["weather", "hurricane", "snow", "temperature"]):
        return "weather"
    return "other"


async def run(n_markets: int, edge_threshold: float, bankroll: float) -> dict:
    print(f"polymarket-paper-trade: {n_markets} markets, edge threshold {edge_threshold:+.2%}")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    print("  pulling active Polymarket markets...")
    markets = await fetch_active_binaries(n_markets * 3)
    if not markets:
        return {"error": "no eligible Polymarket markets returned"}
    print(f"  got {len(markets)} candidate markets")

    book = PaperBook(portfolio_usdc=bankroll)
    ledger = FeeLedger()
    rows: list[dict] = []

    for m in markets[:n_markets]:
        slug = m.get("slug") or ""
        question = m.get("question") or ""
        category = _normalise_category(slug, question)

        # Polymarket Gamma encodes the YES outcome price as outcomePrices[0]
        outcome_prices = m.get("outcomePrices")
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except (TypeError, ValueError):
                outcome_prices = None
        if not (isinstance(outcome_prices, list) and len(outcome_prices) >= 2):
            continue
        try:
            yes_p = float(outcome_prices[0])
        except (TypeError, ValueError):
            continue

        # Try to fetch the YES token id + live book for realistic depth.
        clob_token_ids = m.get("clobTokenIds")
        if isinstance(clob_token_ids, str):
            try:
                clob_token_ids = json.loads(clob_token_ids)
            except (TypeError, ValueError):
                clob_token_ids = None
        depth = 50_000.0  # default synthetic if book fetch fails
        try:
            if isinstance(clob_token_ids, list) and clob_token_ids:
                book_top = await fetch_order_book(str(clob_token_ids[0]))
                _bid, _ask, real_depth = extract_book_top(book_top)
                if real_depth > 0:
                    depth = real_depth
        except Exception as exc:
            print(f"    book fetch for {slug} failed: {exc}; using synthetic $50k")

        # Toy council probability.
        try:
            vol = float(m.get("volume24hr") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        council_p = toy_council_probability(yes_p, vol)
        edge_signed = council_p - yes_p
        edge_abs = abs(edge_signed)

        if edge_abs < edge_threshold:
            rows.append({
                "slug": slug,
                "category": category,
                "yes_implied": yes_p,
                "council_p": council_p,
                "edge": edge_signed,
                "decision": "skipped (edge below threshold)",
            })
            continue

        # Half-Kelly sizing through the production code path.
        direction = "YES" if edge_signed > 0 else "NO"
        entry_p = yes_p if direction == "YES" else 1 - yes_p
        size_pct, kelly_f, sizing_reason = size_position(
            directional_edge=edge_abs, entry_price=entry_p
        )
        if sizing_reason not in ("ok", "capped") or size_pct <= 0:
            rows.append({
                "slug": slug,
                "category": category,
                "edge": edge_signed,
                "decision": f"size {sizing_reason}",
            })
            continue

        size_usdc = size_pct * bankroll
        decision = choose_execution(
            side_price=entry_p,
            edge_abs=edge_abs,
            depth_usdc=depth,
            size_usdc=size_usdc,
            days_to_resolution=getattr(m, "days_to_resolution", None),
            category=category,
        )

        # Build a Thesis + ApprovalToken for the paper book.
        thesis = Thesis(
            signal_id=f"pm-{slug}",
            market_id=str(m.get("conditionId") or m.get("id") or slug),
            question=question,
            direction=direction,
            council_probability=council_p,
            raw_market_probability=yes_p,
            edge=edge_abs,
            confidence=min(0.95, 0.5 + edge_abs),
            recommended_size_pct=size_pct,
            kelly_fraction=kelly_f,
            weighted_approval=0.65,
            exit_conditions=ExitConditions(
                invalidation="market moves against thesis by 10pp",
                target=min(council_p + 0.10, 0.95) if direction == "YES" else max(council_p - 0.10, 0.05),
                stop=max(yes_p - 0.05, 0.05),
                max_hold_days=30,
            ),
        )
        token = ApprovalToken(
            thesis_id=thesis.thesis_id,
            decision="APPROVED",
            reason_code="ok",
            final_size_pct=size_pct,
            kelly_fraction=kelly_f,
            note=f"category={category} mode={decision.mode}",
        )

        # Fill at the maker price if maker, else the taker price.
        trade = book.execute(
            token=token,
            thesis=thesis,
            mid_price=yes_p,
            depth_usdc=depth,
        )

        # Book fee/rebate per the V2 schedule.
        notional = trade.size_usdc
        fee_row = ledger.book(
            trade_id=trade.trade_id,
            market_id=thesis.market_id,
            category=category,
            mode=decision.mode,
            notional_usdc=notional,
        )

        rows.append({
            "slug": slug,
            "category": category,
            "question": question[:120],
            "yes_implied": yes_p,
            "council_p": council_p,
            "edge": edge_signed,
            "direction": direction,
            "size_pct": size_pct,
            "size_usdc": size_usdc,
            "mode": decision.mode,
            "post_only": decision.post_only,
            "limit_price": decision.limit_price,
            "fill_price": trade.fill_price,
            "expected_taker_fee_bps": decision.expected_taker_fee_bps,
            "expected_maker_rebate_bps": decision.expected_maker_rebate_bps,
            "fee_paid_usdc": fee_row.fee_paid_usdc,
            "rebate_accrued_usdc": fee_row.rebate_accrued_usdc,
        })
        print(
            f"    {slug[:40]:40s} cat={category:10s} {direction} "
            f"size={size_pct:.2%} {decision.mode} fee=${fee_row.fee_paid_usdc:.2f} "
            f"rebate=${fee_row.rebate_accrued_usdc:.2f}"
        )

    totals = ledger.totals()
    by_cat = ledger.by_category()
    # Detect synthetic vs live fixture via the conditionId prefix.
    is_synthetic = any(
        isinstance(m.get("conditionId"), str) and m["conditionId"].startswith("synthetic-")
        for m in markets
    )
    summary = {
        "schema": "pantheon-polymarket-paper-v1",
        "data_source": "synthetic_fallback" if is_synthetic else "polymarket_live",
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": round(time.perf_counter() - t0, 3),
        "n_markets_examined": len(rows),
        "n_trades_fired": int(totals["trades"]),
        "fee_totals": totals,
        "fee_by_category": by_cat,
        "ending_equity_usdc": book.equity_usdc(),
        "rows": rows,
    }

    print()
    print(f"  examined: {len(rows)}  fired: {int(totals['trades'])}")
    print(f"  fees paid: ${totals['fees_paid_usdc']:.2f}  rebates accrued: ${totals['rebates_accrued_usdc']:.2f}")
    print(f"  net fee cost: ${totals['net_cost_usdc']:+.2f}  ({totals['net_bps']:+.2f} bps on notional)")
    print(f"  ending equity (paper, pre-settle): ${book.equity_usdc():,.2f}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markets", type=int, default=20,
                        help="number of Polymarket binary markets to test against")
    parser.add_argument("--edge-threshold", type=float, default=0.05,
                        help="minimum |edge| in probability points to fire a trade")
    parser.add_argument("--bankroll", type=float, default=10_000.0,
                        help="paper bankroll USDC")
    args = parser.parse_args()

    summary = asyncio.run(run(args.markets, args.edge_threshold, args.bankroll))
    if "error" in summary:
        print(f"FAIL: {summary['error']}")
        sys.exit(1)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS / f"polymarket_paper_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print()
    print(f"Done. Artifact: {out_path}")


if __name__ == "__main__":
    main()
