"""Tests for the boule calibrator that consumes ostrakon-fit weights."""

from __future__ import annotations

import json
from pathlib import Path


from boule.calibrator import Calibrator


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_file_returns_pass_through(tmp_path: Path):
    cal = Calibrator.from_path(tmp_path / "missing.json")
    assert cal.has("ares") is False
    assert cal.apply("ares", 0.62) == 0.62


def test_identity_passes_through(tmp_path: Path):
    p = tmp_path / "cal.json"
    _write(p, {"ares": {"method": "identity"}})
    cal = Calibrator.from_path(p)
    assert cal.has("ares") is True
    assert cal.apply("ares", 0.42) == 0.42


def test_platt_squashes(tmp_path: Path):
    p = tmp_path / "cal.json"
    _write(
        p,
        {
            "ares": {
                "method": "platt",
                "platt": {"slope": 0.5, "intercept": 0.0},
            }
        },
    )
    cal = Calibrator.from_path(p)
    out = cal.apply("ares", 0.9)
    assert out < 0.9
    assert out > 0.5


def test_isotonic_interpolates(tmp_path: Path):
    p = tmp_path / "cal.json"
    _write(
        p,
        {
            "athena": {
                "method": "isotonic",
                "isotonic": {"x": [0.0, 0.5, 1.0], "y": [0.1, 0.5, 0.85]},
            }
        },
    )
    cal = Calibrator.from_path(p)
    # mid between 0.0 and 0.5 → mid between 0.1 and 0.5
    assert abs(cal.apply("athena", 0.25) - 0.3) < 1e-6
    # Clip below first knot
    assert cal.apply("athena", -0.5) == 0.1


def test_apply_clamps_input_to_unit():
    cal = Calibrator({})
    assert cal.apply("ares", -1.0) == 0.0
    assert cal.apply("ares", 2.0) == 1.0


def test_unknown_agent_returns_input(tmp_path: Path):
    p = tmp_path / "cal.json"
    _write(
        p,
        {"ares": {"method": "platt", "platt": {"slope": 1.0, "intercept": 0.0}}},
    )
    cal = Calibrator.from_path(p)
    assert cal.has("zeus") is False
    assert cal.apply("zeus", 0.7) == 0.7
