"""Tax CSV export.

Generates an IRS Form 8949-friendly CSV from settled Pantheon trades.
The export is *informational only* — the operator's accountant /
tax software ingests it, decides short- vs long-term treatment, and
files the actual forms.

Columns (Form 8949 box A / box D style):
  description           "Polymarket YES — Will BTC hit 100k?"
  acquired              YYYY-MM-DD
  disposed              YYYY-MM-DD
  proceeds              USD on resolution
  cost_basis            USD at entry
  gain_loss             proceeds - cost_basis (signed)
  holding_days          delta between acquired and disposed
  market_id             pass-through for audit
  trade_id              pass-through for audit

We do NOT compute short-vs-long-term (IRS threshold is 365 days plus a
day; let the accountant decide). We DO emit the holding_days column so
downstream tooling has the information.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SettledTrade:
    trade_id: str
    market_id: str
    question: str
    direction: str  # "YES" / "NO"
    entered_at: datetime
    settled_at: datetime
    cost_basis_usd: float  # USD paid at entry
    proceeds_usd: float    # USD received at settlement


COLUMNS = (
    "description",
    "acquired",
    "disposed",
    "proceeds",
    "cost_basis",
    "gain_loss",
    "holding_days",
    "market_id",
    "trade_id",
)


def to_csv_rows(trades: Iterable[SettledTrade]) -> list[dict[str, Any]]:
    """Project settled trades into Form-8949-style CSV rows."""
    rows: list[dict[str, Any]] = []
    for t in trades:
        if t.cost_basis_usd <= 0 and t.proceeds_usd <= 0:
            continue  # cancelled / never filled
        acquired = t.entered_at.date()
        disposed = t.settled_at.date()
        gain = round(t.proceeds_usd - t.cost_basis_usd, 2)
        rows.append({
            "description": f"Polymarket {t.direction} - {t.question.strip()}",
            "acquired": acquired.isoformat(),
            "disposed": disposed.isoformat(),
            "proceeds": round(t.proceeds_usd, 2),
            "cost_basis": round(t.cost_basis_usd, 2),
            "gain_loss": gain,
            "holding_days": (disposed - acquired).days,
            "market_id": t.market_id,
            "trade_id": t.trade_id,
        })
    return rows


def write_csv(trades: Iterable[SettledTrade], path: Path) -> int:
    """Write the CSV file. Returns the number of rows written."""
    rows = to_csv_rows(trades)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate totals for the cover page of a tax packet."""
    short_term = [r for r in rows if r["holding_days"] <= 365]
    long_term = [r for r in rows if r["holding_days"] > 365]
    def _sum(field: str, lst: list[dict[str, Any]]) -> float:
        return round(sum(float(r[field]) for r in lst), 2)
    return {
        "row_count": len(rows),
        "total_proceeds": _sum("proceeds", rows),
        "total_cost_basis": _sum("cost_basis", rows),
        "total_gain_loss": _sum("gain_loss", rows),
        "short_term_count": len(short_term),
        "short_term_gain_loss": _sum("gain_loss", short_term),
        "long_term_count": len(long_term),
        "long_term_gain_loss": _sum("gain_loss", long_term),
        "year_range": _year_range(rows),
    }


def _year_range(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    years = sorted({int(r["disposed"].split("-")[0]) for r in rows if r.get("disposed")})
    if not years:
        return ""
    if years[0] == years[-1]:
        return str(years[0])
    return f"{years[0]}-{years[-1]}"


def make_synthetic_trade(
    trade_id: str,
    market_id: str,
    question: str,
    direction: str,
    entry_iso: str,
    settle_iso: str,
    cost_basis: float,
    proceeds: float,
) -> SettledTrade:
    """Convenience constructor used by tests + the API export route."""
    return SettledTrade(
        trade_id=trade_id,
        market_id=market_id,
        question=question,
        direction=direction,
        entered_at=datetime.fromisoformat(entry_iso),
        settled_at=datetime.fromisoformat(settle_iso),
        cost_basis_usd=cost_basis,
        proceeds_usd=proceeds,
    )


# Re-export the date type for callers that want to compute years from dates.
__all__ = [
    "COLUMNS",
    "SettledTrade",
    "make_synthetic_trade",
    "summary",
    "to_csv_rows",
    "write_csv",
    "date",
]
