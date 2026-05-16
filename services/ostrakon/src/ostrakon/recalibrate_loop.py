"""Recursive calibration loop.

Closes the learning circle:

    Boule deliberates --> Strategos executes --> market resolves
                                              `-> Ostrakon scores
                                              `-> when N new resolutions
                                                  accumulate, refit per-agent
                                                  calibration, swap the file,
                                                  next Boule deliberation
                                                  reads the new numbers.

The daemon watches the Redis pair (strategos:resolutions stream + the
per-agent histories Ostrakon already maintains) and rebuilds
agent_calibrations.json atomically. Boule's Calibrator picks up the new
file on its next deliberation — no restart required because the loader
re-reads the file every call to ``Calibrator.from_env()``.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import redis.asyncio as aioredis
import structlog

from dataclasses import asdict

from ostrakon import agent_calibration as ac

log = structlog.get_logger("ostrakon.recalibrate_loop")

REFRESH_EVERY_N_RESOLUTIONS = int(
    os.environ.get("OSTRAKON_RECAL_EVERY_N_RESOLUTIONS", "5")
)
MIN_SAMPLES_PER_AGENT = int(os.environ.get("OSTRAKON_RECAL_MIN_SAMPLES", "10"))
POLL_INTERVAL_S = float(os.environ.get("OSTRAKON_RECAL_POLL_S", "30"))
COUNTER_KEY = "ostrakon:recal:counter"
LAST_FIT_KEY = "ostrakon:recal:last_fit"
DEFAULT_OUT_PATH = Path(
    os.environ.get(
        "BOULE_AGENT_CALIBRATION_PATH", "agent_calibrations.json"
    )
)


@dataclass
class RecalibrationResult:
    triggered: bool
    n_resolutions_since_last_fit: int
    n_agents_calibrated: int
    output_path: Path


async def _build_dataset_from_redis(redis: aioredis.Redis) -> dict[str, list[tuple[float, int]]]:
    """Pull every per-agent (probability, outcome) pair Ostrakon has accumulated.

    Ostrakon maintains ``ostrakon:state:<agent>`` blobs as it scores
    settled trades; each blob carries the recent prediction history.
    Here we read all of them and reshape into the format
    ``agent_calibration.calibrate_from_csv`` would receive from a CSV.
    """
    out: dict[str, list[tuple[float, int]]] = {}
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="ostrakon:state:*", count=200)
        for k in keys:
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                continue
            agent = k.split(":")[-1] if isinstance(k, str) else k.decode().split(":")[-1]
            preds = data.get("predictions") or []
            pairs: list[tuple[float, int]] = []
            for entry in preds:
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    continue
                try:
                    p = float(entry[0])
                    y = int(entry[1])
                except (TypeError, ValueError):
                    continue
                if 0.0 <= p <= 1.0 and y in (0, 1):
                    pairs.append((p, y))
            if pairs:
                out[agent] = pairs
        if cursor == 0:
            break
    return out


def _fit_from_pairs(
    grouped: dict[str, list[tuple[float, int]]],
) -> dict[str, ac.AgentCalibration]:
    out: dict[str, ac.AgentCalibration] = {}
    for agent, pairs in grouped.items():
        if len(pairs) < MIN_SAMPLES_PER_AGENT:
            continue
        out[agent] = ac._fit_one(agent, pairs)
    return out


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Atomic file swap so Boule never reads a half-written calibration."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp_cal_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass


async def maybe_recalibrate(
    redis: aioredis.Redis,
    out_path: Path = DEFAULT_OUT_PATH,
    *,
    force: bool = False,
) -> RecalibrationResult:
    """Check the resolutions counter; if it has crossed the threshold,
    refit per-agent calibration and write the JSON atomically.

    Returns whether a fit ran and where the file landed.
    """
    counter_str = await redis.get(COUNTER_KEY)
    counter = int(counter_str) if counter_str is not None else 0
    if not force and counter < REFRESH_EVERY_N_RESOLUTIONS:
        return RecalibrationResult(
            triggered=False,
            n_resolutions_since_last_fit=counter,
            n_agents_calibrated=0,
            output_path=out_path,
        )

    grouped = await _build_dataset_from_redis(redis)
    fitted = _fit_from_pairs(grouped)
    payload = {agent: asdict(cal) for agent, cal in fitted.items()}
    _atomic_write_json(out_path, payload)
    await redis.set(COUNTER_KEY, "0")
    await redis.set(LAST_FIT_KEY, str(len(fitted)))
    log.info(
        "ostrakon.recalibrate.fit",
        agents=len(fitted),
        threshold=REFRESH_EVERY_N_RESOLUTIONS,
        out=str(out_path),
    )
    return RecalibrationResult(
        triggered=True,
        n_resolutions_since_last_fit=counter,
        n_agents_calibrated=len(fitted),
        output_path=out_path,
    )


async def increment_counter(redis: aioredis.Redis, by: int = 1) -> int:
    """Bump the resolutions-since-last-fit counter. Call this from the
    Ostrakon resolution handler each time a new market settles.
    """
    return int(await redis.incrby(COUNTER_KEY, by))


async def loop_forever(out_path: Path = DEFAULT_OUT_PATH) -> None:
    """Poll loop suitable for running as its own service inside Docker."""
    redis = await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    log.info(
        "ostrakon.recalibrate.start",
        every_n=REFRESH_EVERY_N_RESOLUTIONS,
        min_samples=MIN_SAMPLES_PER_AGENT,
        out=str(out_path),
        poll_s=POLL_INTERVAL_S,
    )
    try:
        while True:
            try:
                await maybe_recalibrate(redis, out_path)
            except Exception as e:  # noqa: BLE001
                log.warning("ostrakon.recalibrate.error", error=str(e))
            await asyncio.sleep(POLL_INTERVAL_S)
    finally:
        await redis.aclose()
