"""APScheduler-driven async scheduler.

Builds an :class:`AsyncIOScheduler` with one job per :class:`JobSpec`.
Each job is a regular async callable; cron expressions follow
APScheduler's syntax (``*/5 * * * *`` = every 5 minutes).

The scheduler returned is unconfigured at the call site beyond the
job list — start / stop / health are the caller's responsibility,
keeping this module trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger("chronos")


@dataclass(frozen=True)
class JobSpec:
    name: str
    cron: str               # Standard 5-field cron expression
    func: Callable[[], Awaitable[None]]
    description: str = ""


def build_scheduler(jobs: list[JobSpec]) -> AsyncIOScheduler:
    sched = AsyncIOScheduler()
    for j in jobs:
        sched.add_job(
            j.func,
            trigger=CronTrigger.from_crontab(j.cron),
            id=j.name,
            name=j.description or j.name,
            misfire_grace_time=60,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        log.info("chronos.job_registered", name=j.name, cron=j.cron)
    return sched
