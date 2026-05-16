"""Chronos — Pantheon's scheduler.

Drives the council on a cron schedule. Two built-in jobs:

  - ``apollo.scan`` runs the Apollo prefilter against the Polymarket
    CLOB on a cron expression (default every 5 min). Emits scored
    Signal envelopes to the ``apollo:signals`` stream so Boule picks
    them up.
  - ``boule.sweep`` periodically re-evaluates open theses for stale
    signal data, expired deliberations, and orphan traces.

Both schedules are configurable via env (``CHRONOS_APOLLO_CRON`` and
``CHRONOS_SWEEP_CRON``) so operators can dial up / down frequency
without code changes.

Cancellable: the scheduler installs a SIGINT/SIGTERM handler so the
container shuts down cleanly inside Docker Compose.
"""

from __future__ import annotations

from chronos.scheduler import JobSpec, build_scheduler

__all__ = ["JobSpec", "build_scheduler"]
