"""Ostrakon CLI — consumes strategos:trades + market resolutions to score agents.

For each settled trade we read the cached Thesis (knows per-agent
probabilities) and update each agent's Brier + Sharpe + credibility
weight. Weights are mirrored into Redis at ``ostrakon:weights:<agent>``
so Boule's next deliberation reads them at startup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import Thesis, Trade

from ostrakon.metrics import AgentMetrics

log = structlog.get_logger("ostrakon.cli")

TRADES_STREAM = "strategos:trades"
RESOLUTIONS_STREAM = "strategos:resolutions"
WEIGHT_KEY_PREFIX = "ostrakon:weights"
CONSUMER_GROUP = "ostrakon"
DEFAULT_CONSUMER_NAME = os.environ.get("HOSTNAME", "ostrakon-1")


async def _ensure_group(redis: aioredis.Redis, stream: str) -> None:
    try:
        await redis.xgroup_create(name=stream, groupname=CONSUMER_GROUP, id="$", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _record_resolution(redis: aioredis.Redis, payload: dict) -> None:
    trade_id = payload.get("trade_id")
    resolution = payload.get("resolution_yes_price")
    if trade_id is None or resolution is None:
        return
    raw_trade = await redis.get(f"strategos:trade:{trade_id}")
    if not raw_trade:
        return
    try:
        trade = Trade.model_validate_json(raw_trade)
    except Exception:
        return
    raw_thesis = await redis.get(f"boule:thesis:{trade.thesis_id}")
    if not raw_thesis:
        return
    try:
        thesis = Thesis.model_validate_json(raw_thesis)
    except Exception:
        return

    actual = 1 if float(resolution) >= 0.5 else 0
    won = (trade.direction == "YES" and actual == 1) or (trade.direction == "NO" and actual == 0)
    trade_return = (trade.size_usdc * (1 if won else -1)) / max(trade.size_usdc, 1.0)

    for vote in thesis.agents:
        agent = vote.agent
        prob = vote.probability_estimate
        raw = await redis.get(f"ostrakon:state:{agent}")
        if raw:
            state = json.loads(raw)
        else:
            state = {"predictions": [], "returns": []}
        state["predictions"].append([prob, actual])
        state["returns"].append(trade_return)
        # cap history to 200
        state["predictions"] = state["predictions"][-200:]
        state["returns"] = state["returns"][-200:]
        metrics = AgentMetrics(agent=agent)
        metrics.predictions = [(p, o) for p, o in state["predictions"]]
        metrics.returns = state["returns"]
        weight = metrics.credibility_weight()
        await redis.set(f"ostrakon:state:{agent}", json.dumps(state))
        await redis.set(f"{WEIGHT_KEY_PREFIX}:{agent}", f"{weight:.4f}")
        log.info(
            "ostrakon.weight_updated",
            agent=agent,
            brier=round(metrics.brier, 4),
            weight=weight,
            predictions=metrics.prediction_count,
        )

    # Recursive calibration loop: bump the counter so the recalibrate
    # daemon knows another resolution has landed. The daemon itself
    # decides when to refit, swap the JSON file, and let Boule pick it
    # up on its next deliberation.
    try:
        from ostrakon.recalibrate_loop import increment_counter

        await increment_counter(redis, by=1)
    except Exception as e:  # noqa: BLE001
        log.warning("ostrakon.recal_counter_failed", error=str(e))


async def serve(consumer_name: str) -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    await _ensure_group(redis, RESOLUTIONS_STREAM)
    log.info("ostrakon.cli.serve", consumer=consumer_name)
    try:
        while True:
            response = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={RESOLUTIONS_STREAM: ">"},
                count=20,
                block=5000,
            )
            if not response:
                continue
            for _stream, entries in response:
                for entry_id, fields in entries:
                    payload = fields.get("data") if isinstance(fields, dict) else None
                    try:
                        data = json.loads(payload) if payload else {}
                        await _record_resolution(redis, data)
                    except Exception as e:  # noqa: BLE001
                        log.exception("ostrakon.cli.process_failed", error=str(e))
                    await redis.xack(RESOLUTIONS_STREAM, CONSUMER_GROUP, entry_id)
    finally:
        await redis.aclose()


def _cmd_calibrate(in_csv, out_json: str) -> None:
    """Fit per-agent Platt + isotonic calibrators from a backtest CSV."""
    from pathlib import Path

    from ostrakon import agent_calibration as ac

    in_path = Path(in_csv)
    out_path = Path(out_json)
    cals = ac.calibrate_from_csv(in_path)
    ac.dump_json(cals, out_path)
    print(ac.format_report(cals))
    print(f"\nWrote {len(cals)} agent calibration(s) -> {out_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="ostrakon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("serve", help="Score agents from strategos:resolutions")
    sp.add_argument("--consumer-name", default=DEFAULT_CONSUMER_NAME)

    cp = sub.add_parser(
        "calibrate",
        help="Fit per-agent Platt + isotonic calibrators from a backtest CSV.",
    )
    cp.add_argument("--in", dest="in_csv", required=True, help="backtest_per_agent.csv")
    cp.add_argument(
        "--out",
        dest="out_json",
        default="agent_calibrations.json",
        help="Output JSON consumed by boule.calibrator at runtime.",
    )

    rp = sub.add_parser(
        "recalibrate-loop",
        help="Background daemon: refit calibration every N resolutions, "
             "swap agent_calibrations.json atomically so live Boule picks it "
             "up without restart.",
    )
    rp.add_argument(
        "--out",
        dest="out_json",
        default="agent_calibrations.json",
    )

    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(serve(consumer_name=args.consumer_name))
    elif args.cmd == "calibrate":
        _cmd_calibrate(args.in_csv, args.out_json)
    elif args.cmd == "recalibrate-loop":
        from pathlib import Path

        from ostrakon.recalibrate_loop import loop_forever

        asyncio.run(loop_forever(Path(args.out_json)))


if __name__ == "__main__":
    main()
