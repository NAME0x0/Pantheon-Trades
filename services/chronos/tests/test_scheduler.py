"""Tests for the Chronos scheduler factory.

We do not actually start any jobs; we only assert that build_scheduler
wires the JobSpecs into APScheduler correctly.
"""

from __future__ import annotations

import pytest

from chronos.scheduler import JobSpec, build_scheduler


async def _noop() -> None:
    return None


def test_build_scheduler_registers_each_job():
    specs = [
        JobSpec(name="a", cron="*/5 * * * *", func=_noop, description="every five"),
        JobSpec(name="b", cron="0 * * * *", func=_noop, description="hourly"),
    ]
    sched = build_scheduler(specs)
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {"a", "b"}


def test_invalid_cron_rejected():
    with pytest.raises(Exception):
        build_scheduler([JobSpec(name="bad", cron="not-a-cron", func=_noop)])


def test_job_func_is_attached():
    """Confirm the supplied callable is the one the scheduler will fire."""
    sched = build_scheduler(
        [JobSpec(name="x", cron="*/5 * * * *", func=_noop, description="d")]
    )
    job = sched.get_job("x")
    assert job is not None
    assert job.func is _noop
