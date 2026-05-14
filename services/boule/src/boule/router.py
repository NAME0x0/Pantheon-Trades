"""Internal router — dispatch helpers for the Boule consumer.

Currently a thin wrapper that picks between full deliberation and a
degraded fast-path (smaller council + tighter quorum) based on
:mod:`boule.healing` mode.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pantheon_core.schema import Signal, Thesis

from boule.healing.degrade import DegradeMode, FULL, HALTED

DeliberateFn = Callable[[Signal], Awaitable[Thesis]]


async def route(
    signal: Signal,
    mode: DegradeMode,
    *,
    full_path: DeliberateFn,
    fast_path: DeliberateFn,
) -> Thesis:
    if mode is HALTED:
        raise RuntimeError("Boule halted — refusing to deliberate")
    if mode is FULL:
        return await full_path(signal)
    return await fast_path(signal)
