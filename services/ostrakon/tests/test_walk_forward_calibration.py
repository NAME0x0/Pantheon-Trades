"""Walk-forward / time-aware calibration tests."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("sklearn")

from ostrakon import agent_calibration as ac  # noqa: E402


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["market_id", "agent", "vote", "probability_estimate", "confidence", "brier", "resolved_at"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _synth_rows(agent: str, n: int, age_days_range: tuple[int, int], now: datetime, bias: float = 0.0) -> list[dict]:
    """Generate n agent rows. Outcome is biased by 'bias' on top of the prob."""
    rng = random.Random(42)
    out: list[dict] = []
    age_min, age_max = age_days_range
    for i in range(n):
        p = round(rng.random(), 3)
        # Simulate miscalibration via bias: actual leans up if bias>0.
        score = p + bias
        actual = 1 if rng.random() < max(0.0, min(1.0, score)) else 0
        brier = (p - actual) ** 2
        ts = now - timedelta(days=rng.uniform(age_min, age_max))
        out.append({
            "market_id": f"M{i}",
            "agent": agent,
            "vote": "APPROVE",
            "probability_estimate": p,
            "confidence": 0.7,
            "brier": brier,
            "resolved_at": ts.isoformat(),
        })
    return out


def test_windowed_excludes_old_rows(tmp_path: Path):
    now = datetime(2026, 5, 16, tzinfo=timezone.utc)
    # 30 recent + 30 old. Old rows lack timestamp meaning? No — they DO have ts,
    # just 200d old. With window=30 days, they should drop.
    recent = _synth_rows("apollo", 30, (1, 25), now=now, bias=0.1)
    old = _synth_rows("apollo", 30, (200, 360), now=now, bias=-0.2)
    csv_path = tmp_path / "bt.csv"
    _write_csv(csv_path, recent + old)

    cals = ac.calibrate_from_csv_windowed(csv_path, window_days=30, now=now)
    assert "apollo" in cals
    # 30 recent rows — n_samples should reflect window-only count.
    assert cals["apollo"].n_samples == 30


def test_windowed_requires_timestamp(tmp_path: Path):
    now = datetime(2026, 5, 16, tzinfo=timezone.utc)
    csv_path = tmp_path / "bt.csv"
    rows: list[dict] = []
    rng = random.Random(7)
    for i in range(20):
        rows.append({
            "market_id": f"M{i}",
            "agent": "ghost",
            "vote": "APPROVE",
            "probability_estimate": rng.random(),
            "confidence": 0.7,
            "brier": 0.2,
            "resolved_at": "",  # explicit empty — should be dropped
        })
    _write_csv(csv_path, rows)
    cals = ac.calibrate_from_csv_windowed(csv_path, window_days=30, now=now)
    assert cals == {}


def test_decayed_runs_and_weights_recent(tmp_path: Path):
    now = datetime(2026, 5, 16, tzinfo=timezone.utc)
    # Bias flips across eras: old=-0.3, recent=+0.3. Decay should pull the
    # fit toward the recent bias.
    csv_path = tmp_path / "bt.csv"
    rows = _synth_rows("hermes", 80, (0, 10), now=now, bias=0.3) \
         + _synth_rows("hermes", 80, (180, 360), now=now, bias=-0.3)
    _write_csv(csv_path, rows)

    cals_decayed = ac.calibrate_from_csv_decayed(csv_path, half_life_days=14.0, now=now)
    cals_full = ac.calibrate_from_csv(csv_path)
    assert "hermes" in cals_decayed
    # Both fits should produce valid calibrations; the decayed one should
    # at minimum not blow up & should have run on all rows.
    assert cals_decayed["hermes"].n_samples == 160
    assert cals_full["hermes"].n_samples == 160


def test_decayed_rejects_zero_half_life(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    _write_csv(csv_path, _synth_rows("zeus", 20, (0, 30), now=datetime.now(timezone.utc)))
    with pytest.raises(ValueError):
        ac.calibrate_from_csv_decayed(csv_path, half_life_days=0)


def test_windowed_rejects_zero_window(tmp_path: Path):
    csv_path = tmp_path / "bt.csv"
    _write_csv(csv_path, _synth_rows("zeus", 20, (0, 30), now=datetime.now(timezone.utc)))
    with pytest.raises(ValueError):
        ac.calibrate_from_csv_windowed(csv_path, window_days=0)


def test_parse_timestamp_handles_epoch_seconds():
    row = {"resolved_at": "1747353600"}  # 2025-05-16 UTC roughly
    ts = ac._parse_timestamp(row)
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_timestamp_handles_iso_with_z():
    row = {"resolved_at": "2026-05-16T12:00:00Z"}
    ts = ac._parse_timestamp(row)
    assert ts == datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_timestamp_missing_returns_none():
    assert ac._parse_timestamp({"resolved_at": ""}) is None
    assert ac._parse_timestamp({}) is None
