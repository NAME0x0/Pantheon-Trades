"""Tests for the drawdown-aware Kelly multiplier."""

from __future__ import annotations

import pytest

from areopagus.drawdown import (
    DEFAULT_CAP_DRAWDOWN,
    DEFAULT_FLOOR,
    DrawdownState,
    apply_drawdown,
    drawdown_multiplier,
)


def test_no_drawdown_returns_unit_multiplier():
    assert drawdown_multiplier(100.0, 100.0) == 1.0
    assert drawdown_multiplier(120.0, 100.0) == 1.0  # above peak


def test_drawdown_at_cap_returns_floor():
    peak = 100.0
    current = peak * (1.0 - DEFAULT_CAP_DRAWDOWN)
    assert drawdown_multiplier(current, peak) == pytest.approx(DEFAULT_FLOOR)


def test_drawdown_beyond_cap_floors():
    # 50% drawdown — way past the 30% cap — still floors.
    assert drawdown_multiplier(50.0, 100.0) == pytest.approx(DEFAULT_FLOOR)
    assert drawdown_multiplier(0.0, 100.0) == pytest.approx(DEFAULT_FLOOR)


def test_drawdown_linear_in_middle():
    # 15% drawdown midway through a 30% cap = halfway between 1.0 and floor.
    mult = drawdown_multiplier(85.0, 100.0)
    expected = 1.0 - 0.5 * (1.0 - DEFAULT_FLOOR)
    assert mult == pytest.approx(expected, rel=1e-9)


def test_drawdown_state_property():
    s = DrawdownState(current_equity=80, peak_equity=100)
    assert s.drawdown == pytest.approx(0.2)
    s_recovered = DrawdownState(current_equity=120, peak_equity=100)
    assert s_recovered.drawdown == 0.0


def test_drawdown_state_handles_zero_peak():
    s = DrawdownState(current_equity=0.0, peak_equity=0.0)
    assert s.drawdown == 0.0


def test_apply_drawdown_returns_size_and_multiplier():
    adjusted, mult = apply_drawdown(0.05, current_equity=85.0, peak_equity=100.0)
    assert mult == pytest.approx(1.0 - 0.5 * (1.0 - DEFAULT_FLOOR))
    assert adjusted == pytest.approx(0.05 * mult)


def test_apply_drawdown_idempotent_when_at_peak():
    adjusted, mult = apply_drawdown(0.05, current_equity=100.0, peak_equity=100.0)
    assert mult == 1.0
    assert adjusted == 0.05


def test_custom_floor_and_cap():
    # Stricter regime: 0.5 floor, 0.10 cap — 10% DD pushes straight to floor.
    assert drawdown_multiplier(90.0, 100.0, floor=0.5, cap=0.10) == pytest.approx(0.5)
    # 5% DD midway -> 0.75
    assert drawdown_multiplier(95.0, 100.0, floor=0.5, cap=0.10) == pytest.approx(0.75)


def test_zero_peak_returns_unit():
    # No peak history -> no penalty (caller hasn't enabled the feature).
    assert drawdown_multiplier(50.0, 0.0) == 1.0


def test_zero_cap_disables_penalty():
    # Cap of 0 collapses the ramp — degenerate config, no haircut.
    assert drawdown_multiplier(50.0, 100.0, cap=0.0) == 1.0
