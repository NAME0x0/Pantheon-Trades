"""Agent ablation — leave-one-out council Brier scoring.

Inputs: the same per-agent backtest CSV that feeds calibration. For
each market we have one row per agent with ``probability_estimate``
and the binary outcome (recovered from Brier as elsewhere in this
service).

For each candidate agent X we re-compute the council's mean-of-agent
probability *without* X for every market, then report the population
Brier delta vs the all-agents baseline:

    delta_X = brier_without_X - brier_all

Positive delta means leave-one-out is *worse* than baseline -> the
agent was helping. Negative delta means leave-one-out is *better* than
baseline -> the agent is dead weight; retire it. Confidence-weighted
variants are out of scope — this is a first-pass attribution.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AblationRow:
    agent: str
    n_markets: int  # how many markets the agent participated in
    baseline_brier: float
    leave_one_out_brier: float
    delta: float  # baseline - leave_one_out (positive = agent helps)


def _outcome_from_brier(p: float, brier: float) -> int:
    if abs((p - 1.0) ** 2 - brier) < abs((p - 0.0) ** 2 - brier):
        return 1
    return 0


def _load_per_market(path: Path) -> dict[str, list[tuple[str, float, int]]]:
    """Group rows by market: market_id -> list[(agent, p, outcome)]."""
    out: dict[str, list[tuple[str, float, int]]] = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                market = r["market_id"]
                agent = r["agent"]
                p = float(r["probability_estimate"])
                brier = float(r["brier"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (0.0 <= p <= 1.0):
                continue
            out.setdefault(market, []).append((agent, p, _outcome_from_brier(p, brier)))
    return out


def _market_outcome(rows: list[tuple[str, float, int]]) -> int:
    """Each row carries the same outcome; majority vote handles disagreement
    from numerical-recovery edge cases."""
    if not rows:
        return 0
    yes = sum(1 for _, _, y in rows if y == 1)
    no = len(rows) - yes
    return 1 if yes >= no else 0


def _council_brier(by_market: dict[str, list[tuple[str, float, int]]], drop: str | None) -> tuple[float, int]:
    """Return (mean council Brier, number of markets contributing)."""
    total = 0.0
    n = 0
    for rows in by_market.values():
        kept = [(a, p) for a, p, _ in rows if a != drop]
        if not kept:
            continue
        avg_p = sum(p for _, p in kept) / len(kept)
        outcome = _market_outcome(rows)
        total += (avg_p - outcome) ** 2
        n += 1
    if n == 0:
        return 0.0, 0
    return total / n, n


def ablate_from_csv(path: Path) -> list[AblationRow]:
    """Run leave-one-out ablation across every agent that participated."""
    by_market = _load_per_market(path)
    if not by_market:
        return []
    baseline, _ = _council_brier(by_market, drop=None)
    agents = sorted({a for rows in by_market.values() for a, _, _ in rows})

    out: list[AblationRow] = []
    for agent in agents:
        loo, n = _council_brier(by_market, drop=agent)
        market_count = sum(1 for rows in by_market.values() if any(a == agent for a, _, _ in rows))
        out.append(
            AblationRow(
                agent=agent,
                n_markets=market_count,
                baseline_brier=round(baseline, 5),
                leave_one_out_brier=round(loo, 5),
                delta=round(loo - baseline, 5),
            )
        )
    # Sort by delta descending — agents contributing most appear first.
    out.sort(key=lambda r: r.delta, reverse=True)
    return out


def dump_json(rows: list[AblationRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(r) for r in rows], indent=2),
        encoding="utf-8",
    )


def format_report(rows: list[AblationRow]) -> str:
    if not rows:
        return "(no agents — empty backtest)"
    header = f"{'agent':<14}{'markets':>8}{'base':>10}{'loo':>10}{'delta':>10}  verdict"
    sep = "-" * 65
    lines = [header, sep]
    for r in rows:
        verdict = (
            "agent helps" if r.delta > 1e-4 else
            "neutral" if -1e-4 <= r.delta <= 1e-4 else
            "RETIRE — agent hurts"
        )
        lines.append(
            f"{r.agent:<14}{r.n_markets:>8}{r.baseline_brier:>10.4f}"
            f"{r.leave_one_out_brier:>10.4f}{r.delta:>+10.4f}  {verdict}"
        )
    return "\n".join(lines)
