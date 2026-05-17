"""Live paper-trade test against real CoinGecko BTC prices.

This script proves the Strategos paper book + Areopagus half-Kelly sizer
work end-to-end against real, ticking market data — without spending a
single LLM token or touching any exchange.

How it works:
    1. Poll CoinGecko's free `/api/v3/simple/price` endpoint every
       ``LIVE_PAPER_TICK_S`` seconds for BTC/USD.
    2. Synthesise a binary prediction-market question per tick:
         "Will BTC's next-tick close be above this one?"
       Market price = 0.50 (neutral prior). Council probability =
       sigmoid of recent momentum + tiny mean-reversion. Edge =
       council_p - market_p.
    3. When |edge| exceeds ``LIVE_PAPER_EDGE_THRESHOLD``, run the
       Areopagus half-Kelly sizer + Strategos PaperBook.
    4. Settle each filled trade on the NEXT tick using the realised
       up/down outcome. Track equity, win rate, fees.
    5. Emit a JSON artifact under ``artifacts/coingecko_paper_<UTC>.json``.

This is a paper trade. It is not financial advice. It is not running a
council deliberation — the LLM is replaced by a deterministic momentum
estimator so the test stays fast, cheap, and reproducible. The point is
to prove the venue-side plumbing (CoinGecko -> signal -> sizing ->
paper book -> settlement -> PnL artifact) works against real data.

Usage:
    uv run --project services/strategos --with httpx python scripts/live_paper_trade_coingecko.py
or with the venv already prepared:
    python scripts/live_paper_trade_coingecko.py

Env overrides:
    LIVE_PAPER_TICK_S          seconds between price polls (default 12)
    LIVE_PAPER_TICKS           total ticks to sample (default 30)
    LIVE_PAPER_EDGE_THRESHOLD  min |edge| to fire (default 0.04)
    LIVE_PAPER_MOMENTUM_K      momentum lookback ticks (default 3)
    LIVE_PAPER_BANKROLL_USDC   starting paper bankroll (default 10000)
    LIVE_PAPER_DEPTH_USDC      synthetic CLOB depth (default 50000)
    LIVE_PAPER_MODE            poll | history (default history — single
                                 CoinGecko call returns N bars and we
                                 walk them; ``poll`` keeps the old
                                 spaced-poll behaviour for testing but
                                 trips free-tier limits past ~6 calls.)
    LIVE_PAPER_DAYS            history window in days when MODE=history
                                 (default 1; CoinGecko returns ~hourly
                                 bars at <=90 days, otherwise daily)
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"

# Wire services into sys.path so we can use the production sizers
# without a workspace install.
for svc in ("strategos", "areopagus", "packages/pantheon-core"):
    p = ROOT / ("packages" if svc.startswith("packages/") else "services") / svc.split("/")[-1] / "src"
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Imports that depend on the path patch above.
from pantheon_core.schema import ApprovalToken, ExitConditions, Thesis  # noqa: E402

from areopagus.kelly import size_position  # noqa: E402
from strategos.paper import PaperBook  # noqa: E402


# ─── config ──────────────────────────────────────────────────────────


TICK_S = float(os.environ.get("LIVE_PAPER_TICK_S", "12"))
TICKS = int(os.environ.get("LIVE_PAPER_TICKS", "30"))
EDGE_THRESHOLD = float(os.environ.get("LIVE_PAPER_EDGE_THRESHOLD", "0.04"))
MOMENTUM_K = int(os.environ.get("LIVE_PAPER_MOMENTUM_K", "3"))
BANKROLL = float(os.environ.get("LIVE_PAPER_BANKROLL_USDC", "10000"))
DEPTH = float(os.environ.get("LIVE_PAPER_DEPTH_USDC", "50000"))
ASSET = os.environ.get("LIVE_PAPER_ASSET", "bitcoin")
QUOTE = os.environ.get("LIVE_PAPER_QUOTE", "usd")
MODE = os.environ.get("LIVE_PAPER_MODE", "history").lower()
HISTORY_DAYS = os.environ.get("LIVE_PAPER_DAYS", "1")


# ─── CoinGecko fetch ────────────────────────────────────────────────


COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_HISTORY_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"


async def fetch_price() -> tuple[float, str]:
    """Return ``(price, fetched_at_iso)``. Raises on failure.

    Used by MODE=poll. Free tier limits this hard; prefer fetch_history.
    """
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(
            COINGECKO_URL,
            params={"ids": ASSET, "vs_currencies": QUOTE},
            headers={"accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
    price = float(body[ASSET][QUOTE])
    return price, datetime.now(timezone.utc).isoformat()


async def fetch_history(days: str = "1") -> list[tuple[float, str]]:
    """One-shot bar series. CoinGecko returns hourly bars for days<=90.

    Returns a list of ``(price, iso_ts)`` ordered chronologically.
    """
    import httpx

    async with httpx.AsyncClient(timeout=20.0) as http:
        resp = await http.get(
            COINGECKO_HISTORY_URL.format(id=ASSET),
            params={"vs_currency": QUOTE, "days": days},
            headers={"accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
    prices = body.get("prices") or []
    out: list[tuple[float, str]] = []
    for ms, p in prices:
        ts = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()
        out.append((float(p), ts))
    return out


# ─── signal + sizing ─────────────────────────────────────────────────


@dataclass
class Tick:
    seq: int
    price: float
    fetched_at: str
    ret_log: Optional[float] = None    # log return from prior tick
    council_p: Optional[float] = None  # P(next tick higher)
    market_p: float = 0.50
    edge: Optional[float] = None
    direction: Optional[str] = None    # YES / NO / None (no fire)
    size_pct: float = 0.0
    kelly_fraction: float = 0.0
    reason: str = ""
    fill_price: Optional[float] = None
    settled_pnl_usdc: Optional[float] = None  # filled in at next tick
    settle_outcome_yes: Optional[float] = None


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def council_probability(returns: list[float]) -> float:
    """Toy momentum estimator standing in for the council.

    Aggregates the last ``MOMENTUM_K`` log returns through a tanh so the
    output stays in (0, 1) and saturates politely on outliers. The point
    is determinism + zero cost; the production system replaces this with
    the LLM council's blind-vote probability.
    """
    if not returns:
        return 0.50
    window = returns[-MOMENTUM_K:]
    avg = statistics.fmean(window)
    # Scale a typical 12s BTC return (~5e-4) into a useful sigmoid arg.
    return _sigmoid(avg * 250.0)


# ─── run ─────────────────────────────────────────────────────────────


@dataclass
class Run:
    started_at: str
    config: dict
    ticks: list[Tick] = field(default_factory=list)


async def main() -> None:
    if MODE == "history":
        print(f"CoinGecko paper-trade harness — history mode, {HISTORY_DAYS}d window")
    else:
        print(f"CoinGecko paper-trade harness — poll mode, {TICKS} ticks at {TICK_S}s spacing")
    print(f"edge threshold: {EDGE_THRESHOLD:+.2%} | momentum k={MOMENTUM_K}")
    print(f"bankroll: ${BANKROLL:,.0f} USDC | synthetic depth: ${DEPTH:,.0f}\n")

    if MODE == "history":
        bars = await fetch_history(days=HISTORY_DAYS)
        if not bars:
            print("CoinGecko history returned no bars — aborting")
            return
        # Cap to TICKS to keep artifact bounded.
        if len(bars) > TICKS:
            bars = bars[-TICKS:]
        print(f"  fetched {len(bars)} bars  first ${bars[0][0]:,.2f}  last ${bars[-1][0]:,.2f}\n")

    book = PaperBook(portfolio_usdc=BANKROLL)
    run = Run(
        started_at=datetime.now(timezone.utc).isoformat(),
        config={
            "mode": MODE,
            "tick_seconds": TICK_S,
            "ticks": TICKS,
            "edge_threshold": EDGE_THRESHOLD,
            "momentum_k": MOMENTUM_K,
            "bankroll_usdc": BANKROLL,
            "depth_usdc": DEPTH,
            "asset": ASSET,
            "quote": QUOTE,
            "history_days": HISTORY_DAYS if MODE == "history" else None,
        },
    )

    last_price: Optional[float] = None
    open_trades: list[tuple[Tick, ApprovalToken, Thesis]] = []
    log_returns: list[float] = []
    run_start = time.perf_counter()

    total = len(bars) if MODE == "history" else TICKS
    for i in range(total):
        if MODE == "history":
            price, fetched_at = bars[i]
        else:
            try:
                price, fetched_at = await fetch_price()
            except Exception as exc:
                print(f"  [tick {i + 1}/{total}] fetch failed: {exc} — retrying once")
                await asyncio.sleep(2.0)
                try:
                    price, fetched_at = await fetch_price()
                except Exception as exc2:
                    print(f"  [tick {i + 1}/{total}] retry failed: {exc2} — skipping")
                    continue

        ret = None if last_price is None else math.log(price / last_price)
        if ret is not None:
            log_returns.append(ret)

        tick = Tick(seq=i + 1, price=price, fetched_at=fetched_at, ret_log=ret)
        run.ticks.append(tick)

        # Settle anything open with the realised outcome.
        outcome_yes = 0.5 if ret is None else (1.0 if ret > 0 else 0.0)
        if open_trades and ret is not None:
            settle_pnl = 0.0
            for prev_tick, _tok, _thesis in open_trades:
                trade = book.trades[-1] if book.trades else None
                # Find the actual trade object that matches.
                trade = next(
                    (t for t in book.trades if t.thesis_id == _tok.thesis_id and t.status in ("filled", "partial")),
                    None,
                )
                if trade is None:
                    continue
                pnl = book.settle(trade.trade_id, resolution_yes_price=outcome_yes)
                prev_tick.settled_pnl_usdc = pnl
                prev_tick.settle_outcome_yes = outcome_yes
                settle_pnl += pnl
            if settle_pnl != 0.0:
                print(f"  [tick {i + 1}/{total}] settled {len(open_trades)} positions  pnl ${settle_pnl:+.2f}")
            open_trades.clear()

        # Build the next round's signal.
        cp = council_probability(log_returns) if log_returns else 0.50
        edge = cp - 0.50
        tick.council_p = cp
        tick.market_p = 0.50
        tick.edge = edge

        if abs(edge) >= EDGE_THRESHOLD and i < total - 1:
            direction = "YES" if edge > 0 else "NO"
            entry_price = 0.50  # synthetic — mid of the binary
            # Half-Kelly + caps; same code path the prod court uses.
            final_size, kelly_f, sizing_reason = size_position(
                directional_edge=abs(edge),
                entry_price=entry_price,
            )
            tick.direction = direction
            tick.size_pct = final_size
            tick.kelly_fraction = kelly_f
            tick.reason = sizing_reason

            if sizing_reason in ("ok", "capped") and final_size > 0:
                # Mock the production token+thesis pair the paper book
                # expects. We never persist them — they exist only to
                # let the book reuse the same execute() path.
                thesis = Thesis(
                    signal_id=f"cg-{i + 1}",
                    market_id=f"synthetic-btc-tick-{i + 1}",
                    question=f"Will BTC tick {i + 2} > tick {i + 1} (${price:,.0f})?",
                    direction=direction,
                    council_probability=cp,
                    raw_market_probability=0.50,
                    edge=abs(edge),
                    confidence=min(0.95, 0.5 + abs(edge)),
                    recommended_size_pct=final_size,
                    kelly_fraction=kelly_f,
                    weighted_approval=0.65,
                    exit_conditions=ExitConditions(
                        invalidation="next tick resolves the synthetic question",
                        target=1.0,
                        stop=0.0,
                        max_hold_days=1,
                    ),
                )
                token = ApprovalToken(
                    thesis_id=thesis.thesis_id,
                    decision="APPROVED",
                    reason_code="ok",
                    final_size_pct=final_size,
                    kelly_fraction=kelly_f,
                    note=f"momentum cp={cp:.3f}",
                )
                trade = book.execute(
                    token=token,
                    thesis=thesis,
                    mid_price=0.50,
                    depth_usdc=DEPTH,
                )
                tick.fill_price = trade.fill_price
                open_trades.append((tick, token, thesis))
                print(
                    f"  [tick {i + 1}/{total}] BTC ${price:,.2f}  ret {ret:+.4%}  "
                    f"cp {cp:.3f}  edge {edge:+.3f}  -> {direction} size {final_size:.3%}  "
                    f"fill {trade.fill_price:.3f}"
                )
            else:
                print(
                    f"  [tick {i + 1}/{total}] BTC ${price:,.2f}  cp {cp:.3f}  "
                    f"edge {edge:+.3f}  no fire ({sizing_reason})"
                )
        else:
            print(
                f"  [tick {i + 1}/{total}] BTC ${price:,.2f}  "
                f"{('ret ' + format(ret, '+.4%')) if ret is not None else 'priming'}  "
                f"cp {cp:.3f}  edge {edge:+.3f}  flat"
            )

        last_price = price
        if MODE != "history" and i < total - 1:
            await asyncio.sleep(TICK_S)

    # Settle any still-open trades with the last known outcome 0.5
    # (the question is unresolved — treat as a no-info close).
    for prev_tick, _tok, _thesis in open_trades:
        trade = next(
            (t for t in book.trades if t.thesis_id == _tok.thesis_id and t.status in ("filled", "partial")),
            None,
        )
        if trade is None:
            continue
        pnl = book.settle(trade.trade_id, resolution_yes_price=0.50)
        prev_tick.settled_pnl_usdc = pnl
        prev_tick.settle_outcome_yes = 0.50

    total_runtime_s = time.perf_counter() - run_start

    # ─── aggregate ─────────────────────────────────────────────────
    settled_pnls = [t.settled_pnl_usdc for t in run.ticks if t.settled_pnl_usdc is not None]
    wins = [p for p in settled_pnls if p > 0]
    losses = [p for p in settled_pnls if p < 0]
    fired = [t for t in run.ticks if t.direction is not None and t.size_pct > 0]

    equity = book.equity_usdc()
    realised_pnl = book.realised_pnl_usdc
    return_pct = realised_pnl / BANKROLL
    fees = book.fees_paid_usdc
    win_rate = (len(wins) / len(settled_pnls)) if settled_pnls else 0.0

    # Rough Sharpe on per-tick PnL (annualisation here is meaningless
    # for a 30-tick smoke test — we report the raw mean/stdev ratio).
    if len(settled_pnls) >= 2:
        mean = statistics.fmean(settled_pnls)
        sd = statistics.pstdev(settled_pnls)
        sharpe_raw = (mean / sd) if sd > 0 else 0.0
    else:
        sharpe_raw = 0.0

    # Equity peak / max drawdown via cumulative PnL walk.
    eq_curve: list[float] = []
    cum = 0.0
    for p in settled_pnls:
        cum += p
        eq_curve.append(BANKROLL + cum)
    peak = BANKROLL
    max_dd = 0.0
    for e in eq_curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    summary = {
        "schema": "pantheon-coingecko-paper-v1",
        "started_at": run.started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": round(total_runtime_s, 3),
        "config": run.config,
        "ticks": [t.__dict__ for t in run.ticks],
        "summary": {
            "trades_fired": len(fired),
            "trades_settled": len(settled_pnls),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 4),
            "realised_pnl_usdc": round(realised_pnl, 4),
            "return_pct": round(return_pct, 6),
            "fees_paid_usdc": round(fees, 4),
            "ending_equity_usdc": round(equity, 4),
            "max_drawdown_pct": round(max_dd, 6),
            "sharpe_raw_per_tick": round(sharpe_raw, 4),
        },
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS / f"coingecko_paper_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print()
    print(f"Done in {total_runtime_s:.1f}s. Artifact: {out_path}")
    print(
        f"  fired: {len(fired)} | settled: {len(settled_pnls)} | "
        f"wins: {len(wins)} | losses: {len(losses)}"
    )
    print(
        f"  realised pnl: ${realised_pnl:+.2f}  ({return_pct:+.3%})  "
        f"fees: ${fees:.2f}  ending equity: ${equity:,.2f}"
    )
    print(f"  max drawdown: {max_dd:.3%}  sharpe (per-tick raw): {sharpe_raw:+.3f}")


if __name__ == "__main__":
    asyncio.run(main())
