"""Property-based tests for slippage curve invariants."""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, settings  # noqa: E402

from strategos.slippage import (  # noqa: E402
    MAX_SLIPPAGE,
    estimate_slippage,
    slippage_eats_edge,
)


@given(
    size=st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False),
    depth=st.floats(min_value=1.0, max_value=10_000_000, allow_nan=False),
)
@settings(max_examples=400, deadline=None)
def test_slippage_non_negative_and_capped(size: float, depth: float):
    s = estimate_slippage(size, depth)
    assert 0.0 <= s <= MAX_SLIPPAGE + 1e-12


@given(
    size_a=st.floats(min_value=10, max_value=100_000, allow_nan=False),
    size_b=st.floats(min_value=10, max_value=100_000, allow_nan=False),
    depth=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_slippage_monotonic_in_size(size_a: float, size_b: float, depth: float):
    """At a fixed depth, more size never produces less slippage."""
    s_a = estimate_slippage(size_a, depth)
    s_b = estimate_slippage(size_b, depth)
    if size_a <= size_b:
        assert s_a <= s_b + 1e-12
    else:
        assert s_b <= s_a + 1e-12


@given(
    size=st.floats(min_value=10, max_value=100_000, allow_nan=False),
    depth_a=st.floats(min_value=100, max_value=10_000, allow_nan=False),
    depth_b=st.floats(min_value=100, max_value=10_000, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_slippage_monotonic_in_depth(size: float, depth_a: float, depth_b: float):
    """At fixed size, deeper book never produces more slippage."""
    s_a = estimate_slippage(size, depth_a)
    s_b = estimate_slippage(size, depth_b)
    if depth_a >= depth_b:
        assert s_a <= s_b + 1e-12
    else:
        assert s_b <= s_a + 1e-12


@given(
    edge=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
    size=st.floats(min_value=0.0, max_value=100_000, allow_nan=False),
    depth=st.floats(min_value=1.0, max_value=1_000_000, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_slippage_eats_edge_is_consistent(edge: float, size: float, depth: float):
    """slippage_eats_edge agrees with the inequality it claims."""
    out = slippage_eats_edge(size, depth, edge)
    expected = estimate_slippage(size, depth) >= 0.5 * abs(edge)
    assert out == expected


def test_zero_size_zero_slippage():
    assert estimate_slippage(0.0, 1000) == 0.0


def test_zero_depth_is_capped():
    # depth treated as MIN_DEPTH_USDC; tiny depth → max slippage.
    s = estimate_slippage(100, 0.0)
    assert 0.0 <= s <= MAX_SLIPPAGE + 1e-12
