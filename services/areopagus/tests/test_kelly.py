from __future__ import annotations

from areopagus.kelly import KELLY_FRACTION, full_kelly, half_kelly, size_position


def test_full_kelly_basic():
    # entry price 0.5, directional edge 0.10 -> 0.10 / (1-0.5) = 0.20
    assert abs(full_kelly(0.10, 0.5) - 0.20) < 1e-9


def test_full_kelly_high_price():
    # entry price 0.8, edge 0.05 -> 0.05 / 0.2 = 0.25
    assert abs(full_kelly(0.05, 0.8) - 0.25) < 1e-9


def test_full_kelly_no_edge():
    assert full_kelly(0.0, 0.5) == 0.0
    assert full_kelly(-0.05, 0.5) == 0.0


def test_full_kelly_degenerate_price():
    assert full_kelly(0.10, 1.0) == 0.0
    assert full_kelly(0.10, 0.0) == 0.0


def test_half_kelly_is_half_of_full():
    assert abs(half_kelly(0.10, 0.5) - 0.10) < 1e-9
    assert abs(half_kelly(0.10, 0.5) - KELLY_FRACTION * full_kelly(0.10, 0.5)) < 1e-9


def test_size_position_capped():
    size, _, reason = size_position(directional_edge=0.20, entry_price=0.4)
    # half-Kelly would be 0.20/0.6/2 ~ 0.166 > 0.05 cap
    assert reason == "capped"
    assert size == 0.05


def test_size_position_sub_threshold():
    size, _, reason = size_position(directional_edge=0.001, entry_price=0.5)
    assert reason == "sub_threshold"
    assert size == 0.0


def test_size_position_ok():
    size, _, reason = size_position(directional_edge=0.03, entry_price=0.5)
    # half-Kelly = 0.03/0.5/2 = 0.03 — between threshold and cap.
    assert reason == "ok"
    assert size == 0.03


def test_size_position_no_edge():
    _, _, reason = size_position(directional_edge=0.0, entry_price=0.5)
    assert reason == "no_edge"
