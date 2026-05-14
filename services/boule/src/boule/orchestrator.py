"""High-level orchestrator — single entry point used by the API gateway.

For one-shot deliberations (admin REST endpoint, debugging), this
wraps :func:`boule.swarm.deliberate` with the standard env-loading +
client lifecycle.
"""

from __future__ import annotations

from pantheon_core.schema import Signal, Thesis

from boule.swarm import deliberate


async def run_once(signal: Signal) -> Thesis:
    return await deliberate(signal)
