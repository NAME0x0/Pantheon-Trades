"""Tests for ostrakon agent ablation."""

from __future__ import annotations

import csv
from pathlib import Path

from ostrakon.ablation import ablate_from_csv, dump_json, format_report


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["market_id", "agent", "vote", "probability_estimate", "confidence", "brier"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _row(market: str, agent: str, p: float, outcome: int) -> dict:
    return {
        "market_id": market,
        "agent": agent,
        "vote": "APPROVE",
        "probability_estimate": p,
        "confidence": 0.7,
        "brier": (p - outcome) ** 2,
    }


def test_empty_csv_returns_empty(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    _write(csv_path, [])
    assert ablate_from_csv(csv_path) == []


def test_dead_weight_agent_has_negative_delta(tmp_path: Path):
    # 3 markets — outcome=1 for all. "good" predicts well (0.9), "bad" predicts
    # opposite (0.1). Dropping "bad" should improve council Brier
    # -> delta_bad is negative (agent hurts).
    csv_path = tmp_path / "bt.csv"
    rows = []
    for m in ("m1", "m2", "m3"):
        rows.append(_row(m, "good", 0.9, 1))
        rows.append(_row(m, "bad", 0.1, 1))
    _write(csv_path, rows)
    result = ablate_from_csv(csv_path)
    by_agent = {r.agent: r for r in result}
    assert by_agent["bad"].delta < 0  # dropping bad helps -> delta negative
    assert by_agent["good"].delta > 0  # dropping good hurts -> delta positive


def test_market_count_per_agent(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    rows = [
        _row("m1", "alice", 0.7, 1),
        _row("m1", "bob", 0.6, 1),
        _row("m2", "alice", 0.8, 1),
    ]
    _write(csv_path, rows)
    result = ablate_from_csv(csv_path)
    by_agent = {r.agent: r for r in result}
    assert by_agent["alice"].n_markets == 2
    assert by_agent["bob"].n_markets == 1


def test_format_report_smoke(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    _write(csv_path, [_row("m1", "alice", 0.7, 1), _row("m1", "bob", 0.6, 1)])
    result = ablate_from_csv(csv_path)
    text = format_report(result)
    assert "alice" in text
    assert "bob" in text
    assert "delta" in text


def test_format_report_empty():
    assert "no agents" in format_report([])


def test_dump_json_round_trip(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    _write(csv_path, [_row("m1", "alice", 0.7, 1), _row("m1", "bob", 0.6, 1)])
    result = ablate_from_csv(csv_path)
    out = tmp_path / "ablation.json"
    dump_json(result, out)
    import json

    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert {r["agent"] for r in data} == {"alice", "bob"}


def test_outputs_sorted_by_delta_desc(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    rows = []
    for m in ("m1", "m2", "m3"):
        rows.append(_row(m, "good", 0.9, 1))
        rows.append(_row(m, "neutral", 0.5, 1))
        rows.append(_row(m, "bad", 0.1, 1))
    _write(csv_path, rows)
    result = ablate_from_csv(csv_path)
    deltas = [r.delta for r in result]
    assert deltas == sorted(deltas, reverse=True)
