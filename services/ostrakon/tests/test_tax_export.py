"""Tests for the IRS Form 8949 tax export."""

from __future__ import annotations

import csv
from pathlib import Path


from ostrakon.tax_export import (
    COLUMNS,
    SettledTrade,
    make_synthetic_trade,
    summary,
    to_csv_rows,
    write_csv,
)


def _winning_trade() -> SettledTrade:
    return make_synthetic_trade(
        trade_id="t1",
        market_id="m1",
        question="Will BTC hit 100k?",
        direction="YES",
        entry_iso="2026-01-15T12:00:00",
        settle_iso="2026-03-15T12:00:00",
        cost_basis=500.0,
        proceeds=900.0,
    )


def _losing_trade() -> SettledTrade:
    return make_synthetic_trade(
        trade_id="t2",
        market_id="m2",
        question="Will the Fed cut?",
        direction="NO",
        entry_iso="2026-02-01T12:00:00",
        settle_iso="2026-02-15T12:00:00",
        cost_basis=400.0,
        proceeds=0.0,
    )


def _long_term_trade() -> SettledTrade:
    return make_synthetic_trade(
        trade_id="t3",
        market_id="m3",
        question="Will SpaceX reach Mars by 2030?",
        direction="YES",
        entry_iso="2025-01-01T12:00:00",
        settle_iso="2026-05-16T12:00:00",  # ~16 months later
        cost_basis=200.0,
        proceeds=500.0,
    )


def test_csv_columns_match_constant():
    rows = to_csv_rows([_winning_trade()])
    assert set(rows[0].keys()) == set(COLUMNS)


def test_winning_trade_gain():
    rows = to_csv_rows([_winning_trade()])
    assert rows[0]["gain_loss"] == 400.0


def test_losing_trade_loss():
    rows = to_csv_rows([_losing_trade()])
    assert rows[0]["gain_loss"] == -400.0


def test_holding_days_computed():
    rows = to_csv_rows([_winning_trade()])
    assert rows[0]["holding_days"] == 59  # Jan 15 -> Mar 15


def test_cancelled_trade_dropped():
    cancelled = make_synthetic_trade(
        "t0", "m0", "q", "YES",
        "2026-03-01T12:00:00", "2026-03-01T13:00:00",
        cost_basis=0.0,
        proceeds=0.0,
    )
    rows = to_csv_rows([cancelled])
    assert rows == []


def test_write_csv_round_trip(tmp_path: Path):
    out = tmp_path / "export.csv"
    n = write_csv([_winning_trade(), _losing_trade()], out)
    assert n == 2
    with out.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["description"].startswith("Polymarket YES")
    assert float(rows[0]["gain_loss"]) == 400.0


def test_write_csv_creates_parent_dirs(tmp_path: Path):
    out = tmp_path / "sub" / "dir" / "x.csv"
    n = write_csv([_winning_trade()], out)
    assert n == 1
    assert out.exists()


def test_summary_aggregates_short_and_long():
    rows = to_csv_rows([_winning_trade(), _losing_trade(), _long_term_trade()])
    s = summary(rows)
    assert s["row_count"] == 3
    # Two short-term (< 1 yr), one long-term (16 mo).
    assert s["short_term_count"] == 2
    assert s["long_term_count"] == 1
    assert s["total_gain_loss"] == 300.0
    # Year range covers 2026 only (all settled in 2026).
    assert s["year_range"] == "2026"


def test_summary_year_range_multi_year():
    rows = [
        {"holding_days": 1, "proceeds": 100, "cost_basis": 50, "gain_loss": 50, "disposed": "2025-02-15"},
        {"holding_days": 1, "proceeds": 50, "cost_basis": 25, "gain_loss": 25, "disposed": "2026-02-15"},
    ]
    s = summary(rows)
    assert s["year_range"] == "2025-2026"


def test_summary_empty():
    s = summary([])
    assert s["row_count"] == 0
    assert s["total_gain_loss"] == 0.0
    assert s["year_range"] == ""
