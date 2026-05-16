"""Property-based tests for the boule calibrator's invariants."""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, settings  # noqa: E402

from boule.calibrator import Calibrator, _piecewise, _sigmoid  # noqa: E402


@given(z=st.floats(min_value=-50, max_value=50, allow_nan=False))
@settings(max_examples=300, deadline=None)
def test_sigmoid_bounded_unit(z: float):
    out = _sigmoid(z)
    assert 0.0 <= out <= 1.0


@given(
    a=st.floats(min_value=-30, max_value=30, allow_nan=False),
    b=st.floats(min_value=-30, max_value=30, allow_nan=False),
)
@settings(max_examples=200, deadline=None)
def test_sigmoid_monotonic(a: float, b: float):
    if a <= b:
        assert _sigmoid(a) <= _sigmoid(b) + 1e-9
    else:
        assert _sigmoid(b) <= _sigmoid(a) + 1e-9


@given(
    knots=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=2,
        max_size=8,
        unique=True,
    ),
    p=st.floats(min_value=-0.5, max_value=1.5, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_piecewise_clips_outside_range(knots: list[float], p: float):
    xs = sorted(knots)
    ys = [i / (len(xs) - 1) for i in range(len(xs))]  # monotone non-decreasing
    out = _piecewise(xs, ys, p)
    assert ys[0] - 1e-9 <= out <= ys[-1] + 1e-9


@given(
    raw_p=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_apply_clamps_input_to_unit_when_no_calibrator(raw_p: float):
    cal = Calibrator({})
    assert 0.0 <= cal.apply("ghost", raw_p) <= 1.0


@given(
    raw_p=st.floats(min_value=-2.0, max_value=3.0, allow_nan=False),
)
@settings(max_examples=200, deadline=None)
def test_apply_always_in_unit(raw_p: float):
    cal = Calibrator({})
    out = cal.apply("anyone", raw_p)
    assert 0.0 <= out <= 1.0
