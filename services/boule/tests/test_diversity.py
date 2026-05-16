"""Tests for the anti-Goodhart council diversity metric."""

from __future__ import annotations


from boule.diversity import MIN_DIVERSITY, measure


def test_all_approve_low_diversity():
    votes = [("APPROVE", 0.62)] * 10
    d = measure(votes)
    # All same vote, all same probability → entropy 0, std 0.
    assert d.vote_entropy == 0.0
    assert d.probability_std == 0.0
    assert d.composite == 0.0
    assert d.alert is True


def test_evenly_split_high_diversity():
    votes = (
        [("APPROVE", 0.7)] * 4
        + [("REJECT", 0.3)] * 4
        + [("ABSTAIN", 0.5)] * 2
    )
    d = measure(votes)
    # Three labels populated → entropy > 1 bit.
    assert d.vote_entropy > 1.0
    assert d.composite > MIN_DIVERSITY
    assert d.alert is False


def test_spread_with_same_label():
    """All APPROVE but probability estimates diverge."""
    votes = [
        ("APPROVE", 0.55),
        ("APPROVE", 0.65),
        ("APPROVE", 0.72),
        ("APPROVE", 0.51),
        ("APPROVE", 0.78),
    ]
    d = measure(votes)
    # Entropy still 0 (single label), but std > 0 contributes.
    assert d.vote_entropy == 0.0
    assert d.probability_std > 0.0
    # 60% entropy × 0 + 40% std-norm × > 0
    assert d.composite > 0.0


def test_empty_votes_safe():
    d = measure([])
    assert d.vote_entropy == 0.0
    assert d.composite == 0.0
    assert d.alert is True


def test_abstain_not_counted_in_std():
    votes = [
        ("APPROVE", 0.55),
        ("APPROVE", 0.65),
        ("ABSTAIN", 0.5),  # excluded from std
        ("ABSTAIN", 0.5),
    ]
    d_with_abstain = measure(votes)
    votes2 = [("APPROVE", 0.55), ("APPROVE", 0.65)]
    d_no_abstain = measure(votes2)
    # Std should be the same — abstains are not in the prob set.
    assert d_with_abstain.probability_std == d_no_abstain.probability_std


def test_alert_threshold_configurable():
    votes = [("APPROVE", 0.55)] * 5
    high_floor = measure(votes, min_diversity=0.9)
    assert high_floor.alert is True
    low_floor = measure(votes, min_diversity=0.0)
    assert low_floor.alert is False
