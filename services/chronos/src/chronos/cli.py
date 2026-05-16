"""Entry point for the Chronos service.

    uv run python -m chronos.cli            # default schedule
    CHRONOS_APOLLO_CRON='*/2 * * * *' uv run python -m chronos.cli

Reads cron expressions from env (with sensible defaults), wires the
default jobs, blocks until SIGINT / SIGTERM.
"""

from __future__ import annotations

import asyncio
import os
import signal

import structlog

from chronos.jobs import apollo_scan, boule_sweep, restraint_anchor_retry
from chronos.scheduler import JobSpec, build_scheduler

log = structlog.get_logger("chronos.cli")


def _job_specs() -> list[JobSpec]:
    return [
        JobSpec(
            name="apollo_scan",
            cron=os.environ.get("CHRONOS_APOLLO_CRON", "*/5 * * * *"),
            func=apollo_scan,
            description="Apollo market scan against Polymarket CLOB",
        ),
        JobSpec(
            name="boule_sweep",
            cron=os.environ.get("CHRONOS_BOULE_SWEEP_CRON", "*/15 * * * *"),
            func=boule_sweep,
            description="Re-check open theses, stale signals, orphan traces",
        ),
        JobSpec(
            name="restraint_anchor_retry",
            cron=os.environ.get("CHRONOS_ANCHOR_RETRY_CRON", "*/30 * * * *"),
            func=restraint_anchor_retry,
            description="Retry on-chain anchor writes that never landed",
        ),
    ]


async def main() -> None:
    sched = build_scheduler(_job_specs())
    sched.start()
    log.info("chronos.start", jobs=[j.id for j in sched.get_jobs()])

    stop = asyncio.Event()

    def _stop(*_a):
        log.info("chronos.shutdown_requested")
        stop.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _stop)
            except NotImplementedError:
                # Windows asyncio loops don't support add_signal_handler.
                signal.signal(sig, _stop)
    except Exception:  # noqa: BLE001
        # Fallback: no graceful shutdown signal wiring.
        pass

    await stop.wait()
    sched.shutdown(wait=False)
    log.info("chronos.stopped")


if __name__ == "__main__":
    asyncio.run(main())
