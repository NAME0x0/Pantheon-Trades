from __future__ import annotations

from moirai.laws import (
    StrategyState,
    is_valid_transition,
    transition_error,
)


def test_initial_state_is_draft():
    assert StrategyState.DRAFT.value == "DRAFT"


def test_valid_transitions():
    assert is_valid_transition(StrategyState.DRAFT, StrategyState.REGISTERED)
    assert is_valid_transition(StrategyState.REGISTERED, StrategyState.PAPER)
    assert is_valid_transition(StrategyState.PAPER, StrategyState.LIVE)
    assert is_valid_transition(StrategyState.LIVE, StrategyState.SUSPENDED)
    assert is_valid_transition(StrategyState.SUSPENDED, StrategyState.LIVE)
    assert is_valid_transition(StrategyState.LIVE, StrategyState.TERMINATED)


def test_invalid_transitions():
    assert not is_valid_transition(StrategyState.DRAFT, StrategyState.LIVE)
    assert not is_valid_transition(StrategyState.PAPER, StrategyState.REGISTERED)
    assert not is_valid_transition(StrategyState.TERMINATED, StrategyState.LIVE)


def test_transition_error_lists_allowed():
    msg = transition_error(StrategyState.DRAFT, StrategyState.LIVE)
    assert "REGISTERED" in msg
