"""Apply per-agent calibration to council probability estimates.

Reads the calibration JSON produced by
``ostrakon calibrate --out agent_calibrations.json`` and exposes a
single function the debate orchestrator calls before tallying votes.

Calibration is a runtime correction, not a re-vote: the agent's
``vote`` (APPROVE / REJECT / ABSTAIN) and ``confidence`` are left
untouched. Only ``probability_estimate`` is mapped through the agent's
fitted Platt sigmoid or isotonic spline.

The file is optional. If the path is unset, or the file is missing,
or no calibrator covers a given agent, the agent's raw probability
flows through unchanged.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger("boule.calibrator")

DEFAULT_PATH_ENV = "BOULE_AGENT_CALIBRATION_PATH"


@dataclass(frozen=True)
class _AgentCal:
    method: str  # "platt" | "isotonic" | "identity"
    platt: dict | None = None
    isotonic: dict | None = None


class Calibrator:
    def __init__(self, per_agent: dict[str, _AgentCal]):
        self._per_agent = per_agent

    @classmethod
    def from_env(cls) -> "Calibrator":
        path_str = os.environ.get(DEFAULT_PATH_ENV, "agent_calibrations.json")
        return cls.from_path(Path(path_str))

    @classmethod
    def from_path(cls, path: Path) -> "Calibrator":
        if not path.exists():
            log.info("boule.calibrator.no_file", path=str(path))
            return cls({})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            log.warning("boule.calibrator.load_failed", error=str(e), path=str(path))
            return cls({})
        out: dict[str, _AgentCal] = {}
        for agent, data in raw.items():
            method = data.get("method", "identity")
            out[agent] = _AgentCal(
                method=method,
                platt=data.get("platt"),
                isotonic=data.get("isotonic"),
            )
        log.info(
            "boule.calibrator.loaded",
            path=str(path),
            agents=list(out.keys()),
        )
        return cls(out)

    def has(self, agent: str) -> bool:
        return agent in self._per_agent

    def apply(self, agent: str, raw_p: float) -> float:
        """Map a raw probability through the agent's fitted calibrator.

        Falls back to the identity (returns ``raw_p`` clamped to [0, 1])
        when no calibrator is available.
        """
        p = max(0.0, min(1.0, float(raw_p)))
        cal: Optional[_AgentCal] = self._per_agent.get(agent)
        if cal is None or cal.method == "identity":
            return p
        if cal.method == "platt" and cal.platt is not None:
            slope = cal.platt["slope"]
            intercept = cal.platt["intercept"]
            return _sigmoid(slope * p + intercept)
        if cal.method == "isotonic" and cal.isotonic is not None:
            xs = cal.isotonic.get("x") or []
            ys = cal.isotonic.get("y") or []
            return _piecewise(xs, ys, p)
        return p


def _sigmoid(z: float) -> float:
    # Overflow-guarded.
    if z >= 0:
        from math import exp

        return 1.0 / (1.0 + exp(-z))
    from math import exp

    ez = exp(z)
    return ez / (1.0 + ez)


def _piecewise(xs: list[float], ys: list[float], p: float) -> float:
    if not xs:
        return p
    if p <= xs[0]:
        return float(ys[0])
    if p >= xs[-1]:
        return float(ys[-1])
    lo, hi = 0, len(xs) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if xs[mid] <= p:
            lo = mid
        else:
            hi = mid
    x0, x1 = xs[lo], xs[hi]
    y0, y1 = ys[lo], ys[hi]
    if x1 == x0:
        return float(y0)
    return float(y0 + (y1 - y0) * (p - x0) / (x1 - x0))
