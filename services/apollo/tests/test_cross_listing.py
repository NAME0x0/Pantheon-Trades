"""Cross-listing detection tests."""

from __future__ import annotations

import pytest

from apollo.cross_listing import (
    find_cross_listings,
    jaccard,
    normalise,
)


def test_normalise_strips_punctuation_and_stopwords():
    out = normalise("Will Bitcoin trade above $120,000 by 2026-12-31?")
    # ‘will’ + ‘by’ + 2026-12-31 stripped, $120,000 → 120000 (commas collapsed)
    assert "bitcoin" in out
    assert "trade" in out
    assert "120000" in out  # comma-collapsed
    assert "will" not in out
    assert "by" not in out
    assert "2026-12-31" not in out


def test_normalise_empty_input():
    assert normalise("") == []
    assert normalise(None) == []  # type: ignore[arg-type]


def test_normalise_strips_dates_and_months():
    out = normalise("Lakers win in May 2026")
    assert "may" not in out
    assert "2026" not in out
    assert "lakers" in out


def test_normalise_drops_quarter_tokens():
    out = normalise("CPI Q3 above 3.0%")
    assert "q3" not in out


def test_jaccard_identical_sets_one():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint_zero():
    assert jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_partial_overlap():
    assert jaccard({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(0.5)


def test_jaccard_empty_returns_zero():
    assert jaccard(set(), set()) == 0.0


def test_find_cross_listings_simple_match():
    """Two venues, one obvious matching question."""
    ma = [{"id": "M1", "question": "Will Bitcoin trade above $120,000 by Dec 2026?"}]
    mb = [{"id": "K1", "question": "Bitcoin above 120000 by December 2026"}]
    out = find_cross_listings(ma, mb, threshold=0.4)
    assert len(out) == 1
    assert out[0].market_a_id == "M1"
    assert out[0].market_b_id == "K1"
    assert out[0].similarity > 0.4


def test_find_cross_listings_no_match():
    ma = [{"id": "M1", "question": "Will the Lakers win the 2026 NBA Finals?"}]
    mb = [{"id": "K1", "question": "Will inflation exceed 3% in Q3?"}]
    out = find_cross_listings(ma, mb, threshold=0.5)
    assert out == []


def test_find_cross_listings_sorted_by_similarity():
    """Multiple matches must come back highest-first."""
    ma = [{"id": "M1", "question": "Will Bitcoin reach 120000"}]
    mb = [
        {"id": "K1", "question": "Will Bitcoin reach 120000"},  # exact
        {"id": "K2", "question": "Will Bitcoin reach 130000"},  # near
    ]
    out = find_cross_listings(ma, mb, threshold=0.4)
    assert len(out) == 2
    assert out[0].market_b_id == "K1"  # higher similarity first
    assert out[1].market_b_id == "K2"


def test_find_cross_listings_custom_keys():
    ma = [{"market_id": "M1", "title": "Lakers win finals"}]
    mb = [{"event_id": "K1", "name": "Will Lakers win finals"}]
    out = find_cross_listings(
        ma, mb,
        threshold=0.5,
        question_key_a="title",
        question_key_b="name",
        id_key_a="market_id",
        id_key_b="event_id",
    )
    assert len(out) == 1
    assert out[0].market_a_id == "M1"
    assert out[0].market_b_id == "K1"


def test_find_cross_listings_skips_empty_questions():
    ma = [{"id": "M1", "question": ""}, {"id": "M2", "question": "x y z"}]
    mb = [{"id": "K1", "question": ""}]
    out = find_cross_listings(ma, mb, threshold=0.4)
    assert out == []
