"""Bootstrap historical resolved-market data into the local cache.

Populates ``.cache/polymarket_resolved.jsonl`` with N resolved binary
markets so ``tests/backtest_polymarket.py`` can run end-to-end without
scraping live Polymarket (which is geo-blocked from many networks and
heavily rate-limited regardless).

Sources, in order:

  1. **Polymarket Subgraph** (The Graph) — open, free, indexed. Returns
     condition_id + question + outcome + endDate.
  2. **Polymarket gamma-api** — alternative REST surface. Less stable
     schema but covers different markets.
  3. **Manifold Markets dump** — fully open binary markets w/ resolution.
     Used as a synthetic 2nd venue if Polymarket access is blocked.

Each source is best-effort: failures are logged and the script moves
on. The total reflects what landed in the cache.

Usage:

    uv run python tests/bootstrap_historical_data.py --limit 500
    uv run python tests/bootstrap_historical_data.py --source manifold
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
OUT_FILE = CACHE_DIR / "polymarket_resolved.jsonl"
DEFAULT_TIMEOUT = 30.0

# Polymarket subgraph at The Graph hosted service (legacy) — the
# main hosted endpoint moved a few times; we try the most common
# variants and the first to respond wins.
SUBGRAPH_ENDPOINTS = [
    "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets",
    "https://api.thegraph.com/subgraphs/name/polymarket/polymarket",
]
GAMMA_API = "https://gamma-api.polymarket.com/markets"
MANIFOLD_API = "https://api.manifold.markets/v0/markets"


# ─── Polymarket subgraph ──────────────────────────────────────────────


SUBGRAPH_QUERY = """
{
  fixedProductMarketMakers(
    first: %d,
    where: { outcomeTokenAmounts_not: null }
    orderBy: lastActiveDay
    orderDirection: desc
  ) {
    id
    conditions {
      id
      question
      resolutionTimestamp
      payoutNumerators
    }
    outcomeTokenAmounts
    collateralVolume
    lastActiveDay
  }
}
"""


async def fetch_subgraph(limit: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http:
        for endpoint in SUBGRAPH_ENDPOINTS:
            try:
                r = await http.post(
                    endpoint,
                    json={"query": SUBGRAPH_QUERY % limit},
                )
                if r.status_code != 200:
                    continue
                payload = r.json()
                if "data" not in payload:
                    continue
                items = (payload["data"] or {}).get("fixedProductMarketMakers") or []
                rows: list[dict] = []
                for m in items:
                    rows.extend(_parse_subgraph(m))
                if rows:
                    return rows[:limit]
            except Exception as e:  # noqa: BLE001
                print(f"[bootstrap] subgraph {endpoint} failed: {e}")
                continue
    return []


def _parse_subgraph(m: dict) -> Iterable[dict]:
    conditions = m.get("conditions") or []
    volume = float(m.get("collateralVolume") or 0)
    for c in conditions:
        if not c.get("resolutionTimestamp"):
            continue
        try:
            payouts = c.get("payoutNumerators") or []
            outcome_yes = bool(payouts and float(payouts[0]) > 0)
        except (ValueError, TypeError):
            continue
        try:
            ts = int(c["resolutionTimestamp"])
        except (TypeError, ValueError):
            continue
        from datetime import datetime, timezone

        yield {
            "condition_id": c.get("id") or m.get("id"),
            "question": c.get("question") or "",
            "category": "subgraph",
            "outcome_yes": outcome_yes,
            "end_date": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "pre_resolution_p": 0.5,  # subgraph does not expose this directly
            "volume_24h": volume,
        }


# ─── Polymarket gamma-api ─────────────────────────────────────────────


async def fetch_gamma(limit: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http:
        try:
            r = await http.get(
                GAMMA_API,
                params={"closed": "true", "limit": limit, "active": "false"},
            )
            r.raise_for_status()
            payload = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"[bootstrap] gamma-api failed: {e}")
            return []
    items = payload if isinstance(payload, list) else (payload.get("data") or [])
    out: list[dict] = []
    for m in items[:limit]:
        try:
            out.append(_parse_gamma(m))
        except Exception:  # noqa: BLE001
            continue
    return [r for r in out if r]


def _parse_gamma(m: dict) -> dict | None:
    if not m.get("endDate"):
        return None
    # Gamma marks 'closed' = true after resolution; outcome encoded
    # in outcomePrices (outcomes is just labels — we don't currently
    # use them, parsing intentionally skipped).
    outcome_yes = False
    outcome_prices = m.get("outcomePrices")
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except (ValueError, TypeError):
            outcome_prices = []
    if outcome_prices and isinstance(outcome_prices, list):
        try:
            outcome_yes = float(outcome_prices[0]) >= 0.99
        except (TypeError, ValueError, IndexError):
            outcome_yes = False
    return {
        "condition_id": m.get("conditionId") or m.get("id"),
        "question": m.get("question") or "",
        "category": (m.get("category") or "polymarket"),
        "outcome_yes": outcome_yes,
        "end_date": m.get("endDate"),
        "pre_resolution_p": float(m.get("lastTradePrice") or 0.5),
        "volume_24h": float(m.get("volume24hr") or 0.0),
    }


# ─── Manifold Markets ─────────────────────────────────────────────────


async def fetch_manifold(limit: int) -> list[dict]:
    """Pull resolved binary markets from Manifold.

    Manifold paginates 1000 at a time via ``before=<id>``; we walk
    forward until we have ``limit`` resolved binary markets.
    """
    out: list[dict] = []
    cursor: str | None = None
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http:
        while len(out) < limit:
            try:
                params: dict[str, Any] = {"limit": 1000}
                if cursor:
                    params["before"] = cursor
                r = await http.get(MANIFOLD_API, params=params)
                r.raise_for_status()
                items = r.json()
            except Exception as e:  # noqa: BLE001
                print(f"[bootstrap] manifold failed: {e}")
                break
            if not items:
                break
            cursor = items[-1].get("id")
            for m in items:
                if m.get("outcomeType") != "BINARY":
                    continue
                if not m.get("isResolved"):
                    continue
                row = _parse_manifold(m)
                if row:
                    out.append(row)
                    if len(out) >= limit:
                        break
            if not cursor:
                break
    return out


def _parse_manifold(m: dict) -> dict | None:
    resolution = (m.get("resolution") or "").upper()
    if resolution not in {"YES", "NO"}:
        return None
    from datetime import datetime, timezone

    rt = m.get("resolutionTime")
    if isinstance(rt, (int, float)):
        end_date = datetime.fromtimestamp(rt / 1000, tz=timezone.utc).isoformat()
    else:
        end_date = (m.get("closeDate") or "")
    return {
        "condition_id": m.get("id"),
        "question": m.get("question") or "",
        "category": "manifold",
        "outcome_yes": resolution == "YES",
        "end_date": end_date,
        "pre_resolution_p": float(m.get("probability") or 0.5),
        "volume_24h": float(m.get("volume") or 0.0),
    }


# ─── Writer ───────────────────────────────────────────────────────────


def _append_jsonl(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line).get("condition_id") or "")
                except Exception:  # noqa: BLE001
                    pass
    appended = 0
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            cid = r.get("condition_id")
            if not cid or cid in seen:
                continue
            f.write(json.dumps(r) + "\n")
            seen.add(cid)
            appended += 1
    return appended


# ─── CLI ──────────────────────────────────────────────────────────────


async def main() -> int:
    parser = argparse.ArgumentParser(prog="bootstrap_historical_data")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument(
        "--source",
        choices=("subgraph", "gamma", "manifold", "all"),
        default="all",
    )
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    args = parser.parse_args()

    total = 0
    if args.source in ("subgraph", "all"):
        print("[bootstrap] pulling Polymarket subgraph...")
        rows = await fetch_subgraph(args.limit)
        added = _append_jsonl(args.out, rows)
        print(f"  + {added} markets from subgraph (received {len(rows)})")
        total += added
    if args.source in ("gamma", "all"):
        print("[bootstrap] pulling Polymarket gamma-api...")
        rows = await fetch_gamma(args.limit)
        added = _append_jsonl(args.out, rows)
        print(f"  + {added} markets from gamma-api (received {len(rows)})")
        total += added
    if args.source in ("manifold", "all"):
        print("[bootstrap] pulling Manifold Markets...")
        rows = await fetch_manifold(args.limit)
        added = _append_jsonl(args.out, rows)
        print(f"  + {added} markets from Manifold (received {len(rows)})")
        total += added

    if total == 0:
        print("\n[bootstrap] no markets fetched. Check network access — the")
        print("            Polymarket endpoints are geo-restricted in many")
        print("            regions; Manifold is usually reachable from anywhere.")
        return 1

    print(f"\n[bootstrap] {total} new resolved markets cached at {args.out}")
    print("            run `uv run python tests/backtest_polymarket.py` to replay.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
