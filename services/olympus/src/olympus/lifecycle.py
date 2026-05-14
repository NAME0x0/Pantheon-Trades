"""Lifecycle helper — bridges Olympus state into Moirai actions.

When Olympus pauses, all Moirai strategies move to SUSPENDED. When Olympus
recovers, the operator must explicitly re-promote each suspended strategy.
"""

from __future__ import annotations

from olympus.state import OlympusState, SystemState


def should_suspend_all_strategies(state: OlympusState) -> bool:
    return state.state in (SystemState.PAUSED, SystemState.DEGRADED)


def can_promote_strategies(state: OlympusState) -> bool:
    return state.state is SystemState.ACTIVE
