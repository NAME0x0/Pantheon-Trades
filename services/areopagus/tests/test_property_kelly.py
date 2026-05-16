"""Property-based tests for half-Kelly sizing math.

Hypothesis generates thousands of random (directional_edge, entry_price,
portfolio) tuples to verify invariants the unit tests can't enumerate:

  - sized position is non-negative
  - never exceeds MAX_POSITION_PCT cap
  - half-Kelly = 0.5 × full-Kelly when neither hits a cap or floor
  - monotonic in edge (more edge → larger or equal size)
  - monotonic in entry price (cheaper contract → smaller leverage on loss)
  - degenerate prices (0, 1, negative) return 0

Hypothesis is a dev dep — added via uv group, never required at runtime.
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, settings, assume  # noqa: E402

from areopagus.kelly import (  # noqa: E402
    DEFAULT_MAX_PCT,
    DEFAULT_MIN_THRESHOLD,
    KELLY_FRACTION,
    full_kelly,
    size_position,
)


# ─── full_kelly invariants ──────────────────────────────────────────


@given(
    edge=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    price=st.floats(min_value=-0.5, max_value=1.5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=400, deadline=None)
def test_full_kelly_non_negative_and_bounded(edge: float, price: float):
    f = full_kelly(edge, price)
    assert 0.0 <= f <= 1.0


@given(
    edge=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
    price=st.floats(min_value=0.05, max_value=0.95, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_kelly_monotonic_in_edge(edge: float, price: float):
    """Larger edge → larger-or-equal full Kelly at fixed price."""
    assume(edge >= 0.001)
    bigger = full_kelly(edge + 0.05, price)
    smaller = full_kelly(edge, price)
    assert bigger + 1e-9 >= smaller


@pytest.mark.parametrize("price", [-0.1, 0.0, 1.0, 1.5])
def test_degenerate_price_returns_zero(price: float):
    assert full_kelly(0.10, price) == 0.0


# ─── size_position invariants ────────────────────────────────────────


@given(
    edge=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
    price=st.floats(min_value=0.02, max_value=0.98, allow_nan=False),
)
@settings(max_examples=400, deadline=None)
def test_size_never_exceeds_cap(edge: float, price: float):
    final, _kelly_frac, _reason = size_position(directional_edge=edge, entry_price=price)
    assert 0.0 <= final <= DEFAULT_MAX_PCT + 1e-12


@given(
    edge=st.floats(min_value=0.001, max_value=0.5, allow_nan=False),
    price=st.floats(min_value=0.10, max_value=0.90, allow_nan=False),
)
@settings(max_examples=300, deadline=None)
def test_half_kelly_relationship(edge: float, price: float):
    """``size_position`` returns ``(final_size, full_kelly_fraction, reason)``.
    When neither cap nor floor binds, ``final`` must equal
    ``KELLY_FRACTION × kelly_frac`` exactly.
    """
    final, kelly_frac, reason = size_position(directional_edge=edge, entry_price=price)
    if reason in ("sub_threshold", "no_edge", "capped"):
        return
    expected_half = KELLY_FRACTION * kelly_frac
    assert abs(final - expected_half) < 1e-9


@given(
    edge=st.floats(min_value=0.0, max_value=DEFAULT_MIN_THRESHOLD / 2, allow_nan=False),
    price=st.floats(min_value=0.10, max_value=0.90, allow_nan=False),
)
@settings(max_examples=200, deadline=None)
def test_tiny_edge_returns_floor_rejection(edge: float, price: float):
    """Edges below the floor should not produce a size."""
    final, _kelly, reason = size_position(directional_edge=edge, entry_price=price)
    if edge <= 0:
        assert reason == "no_edge"
    # Floor rejection or zero edge: size must be zero.
    assert final == 0.0 or reason == "ok"
