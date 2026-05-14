"""Graceful degradation — pick a fallback debate mode when full council fails."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DegradeMode:
    name: str
    min_quorum: int
    require_zeus: bool
    require_solon: bool


FULL = DegradeMode(name="full", min_quorum=7, require_zeus=True, require_solon=True)
LIMITED = DegradeMode(name="limited", min_quorum=5, require_zeus=True, require_solon=False)
EMERGENCY = DegradeMode(name="emergency", min_quorum=3, require_zeus=True, require_solon=False)
HALTED = DegradeMode(name="halted", min_quorum=999, require_zeus=True, require_solon=False)


def pick_mode(healthy_agents: int, zeus_up: bool, solon_up: bool) -> DegradeMode:
    if healthy_agents >= 8 and zeus_up and solon_up:
        return FULL
    if healthy_agents >= 6 and zeus_up:
        return LIMITED
    if healthy_agents >= 4 and zeus_up:
        return EMERGENCY
    return HALTED
