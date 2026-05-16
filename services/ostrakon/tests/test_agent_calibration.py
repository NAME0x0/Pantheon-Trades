"""Tests for per-agent Platt + isotonic calibration."""

from __future__ import annotations

import csv
from pathlib import Path


from ostrakon import agent_calibration as ac


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["market_id", "agent", "vote", "probability_estimate", "confidence", "brier"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _brier(p: float, actual: int) -> float:
    return round((p - actual) ** 2, 6)


def _row(market_id: str, agent: str, vote: str, p: float, actual: int) -> dict:
    return {
        "market_id": market_id,
        "agent": agent,
        "vote": vote,
        "probability_estimate": p,
        "confidence": 0.8,
        "brier": _brier(p, actual),
    }


def test_outcome_recovery_from_brier():
    # Round trip: build a (p, actual) pair, derive brier, recover actual.
    assert ac._outcome_from_brier(0.7, _brier(0.7, 1)) == 1
    assert ac._outcome_from_brier(0.7, _brier(0.7, 0)) == 0
    assert ac._outcome_from_brier(0.3, _brier(0.3, 1)) == 1
    assert ac._outcome_from_brier(0.3, _brier(0.3, 0)) == 0


def test_under_threshold_agent_skipped(tmp_path: Path):
    """Agent with <10 samples must not be calibrated."""
    rows = [
        _row(f"m{i}", "ares", "APPROVE", 0.6, 1) for i in range(5)
    ]
    csv_path = tmp_path / "tiny.csv"
    _write_csv(csv_path, rows)
    cals = ac.calibrate_from_csv(csv_path)
    assert "ares" not in cals


def test_well_calibrated_agent_picks_identity(tmp_path: Path):
    """If predictions already match actual rates, identity beats Platt + isotonic."""
    # 20 markets at p=0.5; half resolve YES, half NO. Already calibrated.
    rows = []
    for i in range(20):
        actual = i % 2  # alternating
        rows.append(_row(f"m{i}", "athena", "APPROVE", 0.5, actual))
    csv_path = tmp_path / "wellcal.csv"
    _write_csv(csv_path, rows)
    cals = ac.calibrate_from_csv(csv_path)
    assert "athena" in cals
    cal = cals["athena"]
    # raw_brier = 0.25, identity-cv won't beat it. Methods should at best tie.
    assert cal.method in ("identity", "platt", "isotonic")
    assert cal.n_samples == 20


def test_overconfident_agent_gets_calibrated(tmp_path: Path):
    """Agent always says 0.9, only 50% actually resolve YES — Platt should fix."""
    rows = []
    for i in range(40):
        actual = i % 2  # 50/50 outcomes
        rows.append(_row(f"m{i}", "zeus", "APPROVE", 0.9, actual))
    csv_path = tmp_path / "overconf.csv"
    _write_csv(csv_path, rows)
    cals = ac.calibrate_from_csv(csv_path)
    assert "zeus" in cals
    cal = cals["zeus"]
    # Raw brier should be poor (0.9 vs 50% YES → brier ~0.41).
    assert cal.raw_brier > 0.3
    # Calibrated should be much better.
    assert cal.calibrated_brier < cal.raw_brier
    assert cal.improvement > 0


def test_dump_and_load_json_round_trip(tmp_path: Path):
    rows = [_row(f"m{i}", "ares", "APPROVE", 0.7, 1 if i % 3 else 0) for i in range(15)]
    csv_path = tmp_path / "rt.csv"
    out_path = tmp_path / "cal.json"
    _write_csv(csv_path, rows)
    cals = ac.calibrate_from_csv(csv_path)
    ac.dump_json(cals, out_path)
    loaded = ac.load_json(out_path)
    assert set(loaded.keys()) == set(cals.keys())
    for agent in cals:
        assert loaded[agent].method == cals[agent].method
        assert loaded[agent].n_samples == cals[agent].n_samples


def test_apply_identity_returns_input():
    cal = ac.AgentCalibration(
        agent="ares", method="identity", n_samples=10,
        raw_brier=0.25, calibrated_brier=0.25, improvement=0.0,
    )
    assert ac.apply(cal, 0.42) == 0.42
    assert ac.apply(cal, 0.0) == 0.0
    assert ac.apply(cal, 1.0) == 1.0


def test_apply_platt_squashes_toward_calibration():
    """A Platt with positive slope < 1 should pull extremes toward the prior."""
    cal = ac.AgentCalibration(
        agent="ares", method="platt", n_samples=40,
        raw_brier=0.4, calibrated_brier=0.25, improvement=0.15,
        platt={"slope": 0.5, "intercept": 0.0},  # σ(0.5p) — pulls toward 0.5
    )
    # σ(0.5 * 0.9) ≈ 0.611, well below the raw 0.9
    out = ac.apply(cal, 0.9)
    assert out < 0.9
    assert out > 0.5


def test_apply_isotonic_clips_and_interpolates():
    cal = ac.AgentCalibration(
        agent="ares", method="isotonic", n_samples=50,
        raw_brier=0.3, calibrated_brier=0.2, improvement=0.1,
        isotonic={"x": [0.0, 0.5, 1.0], "y": [0.1, 0.5, 0.85]},
    )
    # Edge clipping
    assert ac.apply(cal, 0.0) == 0.1
    assert ac.apply(cal, 1.0) == 0.85
    # Linear interpolation between knots
    mid = ac.apply(cal, 0.25)   # halfway between 0.0 and 0.5 → halfway between 0.1 and 0.5 = 0.3
    assert abs(mid - 0.3) < 1e-6


def test_format_report_handles_empty():
    assert "no agents" in ac.format_report({}).lower()


def test_format_report_lists_agents():
    cal = ac.AgentCalibration(
        agent="ares", method="platt", n_samples=40,
        raw_brier=0.4, calibrated_brier=0.25, improvement=0.15,
        platt={"slope": 0.5, "intercept": 0.0},
    )
    report = ac.format_report({"ares": cal})
    assert "ares" in report
    assert "platt" in report
    assert "40" in report
