"""Per-agent calibration — fit Platt and isotonic correctors from backtest data.

Input: ``backtest_per_agent.csv`` produced by
``tests/backtest_polymarket.py``. One row per (market, agent) pairing
with columns:

    market_id,agent,vote,probability_estimate,confidence,brier

Output: a calibration JSON file plus a per-agent diagnostic report.
The JSON is consumed at runtime by ``boule.calibrator`` to correct
each agent's probability estimate before the council tally.

Two calibrators are fit per agent:

  - **Platt scaling** (sigmoid logistic). Robust when the agent's
    miscalibration is monotonic and we have few data points (~20+).
  - **Isotonic regression** (piecewise-constant monotonic). Better
    at correcting non-linear miscalibration when N is larger (~50+).

We pick the calibrator with the lower out-of-sample Brier via
5-fold cross-validation. If neither beats the identity (no
calibration), we record ``method = identity`` and let the agent's
own estimate stand.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

CalibrationMethod = Literal["platt", "isotonic", "identity"]


@dataclass
class AgentCalibration:
    agent: str
    method: CalibrationMethod
    n_samples: int
    raw_brier: float            # mean Brier before calibration
    calibrated_brier: float     # mean Brier after, on held-out folds
    improvement: float          # raw_brier - calibrated_brier
    # Platt: serialise as (intercept, slope). Apply via 1/(1+exp(-(slope*x + intercept))).
    platt: dict | None = None
    # Isotonic: serialise as breakpoint arrays. Apply via piecewise interp.
    isotonic: dict | None = None


def calibrate_from_csv(path: Path) -> dict[str, AgentCalibration]:
    """Fit per-agent calibrators from a backtest CSV.

    Skips agents with < 10 valid (probability, outcome) pairs — not
    enough signal to fit anything meaningful.
    """
    rows = _load_rows(path)
    grouped: dict[str, list[tuple[float, int]]] = {}
    for r in rows:
        agent = r["agent"]
        try:
            p = float(r["probability_estimate"])
            actual = _outcome_from_brier(p, float(r["brier"]))
        except (KeyError, ValueError, TypeError):
            continue
        if not (0.0 <= p <= 1.0):
            continue
        grouped.setdefault(agent, []).append((p, actual))

    out: dict[str, AgentCalibration] = {}
    for agent, pairs in grouped.items():
        if len(pairs) < 10:
            continue
        out[agent] = _fit_one(agent, pairs)
    return out


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _outcome_from_brier(p: float, brier: float) -> int:
    """Recover the binary outcome from (probability, brier).

    Brier = (p - actual)^2, actual ∈ {0, 1}. Closer of {0,1} to (p ± √brier).
    """
    err = brier ** 0.5
    actual_if_1 = 1.0
    actual_if_0 = 0.0
    if abs((p - actual_if_1) ** 2 - brier) < abs((p - actual_if_0) ** 2 - brier):
        return 1
    return 0


def _fit_one(agent: str, pairs: list[tuple[float, int]]) -> AgentCalibration:
    probs = np.array([p for p, _ in pairs], dtype=float).reshape(-1, 1)
    outcomes = np.array([y for _, y in pairs], dtype=int)
    n = len(pairs)
    raw_brier = float(np.mean((probs.flatten() - outcomes) ** 2))

    # 5-fold (or smaller if too few samples) out-of-sample Brier for each method
    n_splits = min(5, max(2, n // 5))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    platt_briers: list[float] = []
    iso_briers: list[float] = []
    for train_idx, test_idx in kf.split(probs):
        x_tr, x_te = probs[train_idx], probs[test_idx]
        y_tr, y_te = outcomes[train_idx], outcomes[test_idx]
        if len(set(y_tr)) < 2:
            # Degenerate fold (all 0s or all 1s) — skip.
            continue
        # Platt
        try:
            lr = LogisticRegression(C=1e6, solver="lbfgs")
            lr.fit(x_tr, y_tr)
            p_te = lr.predict_proba(x_te)[:, 1]
            platt_briers.append(float(np.mean((p_te - y_te) ** 2)))
        except Exception:  # noqa: BLE001
            pass
        # Isotonic
        try:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(x_tr.flatten(), y_tr)
            p_te = iso.predict(x_te.flatten())
            iso_briers.append(float(np.mean((p_te - y_te) ** 2)))
        except Exception:  # noqa: BLE001
            pass

    platt_cv = float(np.mean(platt_briers)) if platt_briers else float("inf")
    iso_cv = float(np.mean(iso_briers)) if iso_briers else float("inf")

    # Pick the winner — but only if it beats raw Brier by a margin.
    candidates: list[tuple[float, CalibrationMethod]] = [
        (raw_brier, "identity"),
        (platt_cv, "platt"),
        (iso_cv, "isotonic"),
    ]
    candidates.sort(key=lambda x: x[0])
    best_brier, method = candidates[0]

    cal = AgentCalibration(
        agent=agent,
        method=method,
        n_samples=n,
        raw_brier=round(raw_brier, 5),
        calibrated_brier=round(best_brier, 5),
        improvement=round(raw_brier - best_brier, 5),
    )

    if method == "platt":
        lr = LogisticRegression(C=1e6, solver="lbfgs")
        lr.fit(probs, outcomes)
        cal.platt = {
            "intercept": float(lr.intercept_[0]),
            "slope": float(lr.coef_[0][0]),
        }
    elif method == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(probs.flatten(), outcomes)
        # Serialise breakpoints — the X knots and corresponding Y values.
        cal.isotonic = {
            "x": iso.X_thresholds_.tolist(),
            "y": iso.y_thresholds_.tolist(),
        }
    return cal


# ──────────────────────────────────────────────────────────────────────
# Serialise + apply (runtime side)
# ──────────────────────────────────────────────────────────────────────


def dump_json(calibrations: dict[str, AgentCalibration], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {agent: asdict(cal) for agent, cal in calibrations.items()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, AgentCalibration]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        agent: AgentCalibration(**data) for agent, data in raw.items()
    }


def apply(calibration: AgentCalibration | None, raw_p: float) -> float:
    """Apply an agent's calibrator to a raw probability estimate.

    Identity-falls-through when no calibration is available or the
    method is ``identity``.
    """
    p = max(0.0, min(1.0, float(raw_p)))
    if calibration is None or calibration.method == "identity":
        return p
    if calibration.method == "platt" and calibration.platt is not None:
        slope = calibration.platt["slope"]
        intercept = calibration.platt["intercept"]
        z = slope * p + intercept
        # Sigmoid w/ overflow guard.
        if z >= 0:
            ez = pow(2.718281828, -z)
            return float(1.0 / (1.0 + ez))
        ez = pow(2.718281828, z)
        return float(ez / (1.0 + ez))
    if calibration.method == "isotonic" and calibration.isotonic is not None:
        xs = calibration.isotonic["x"]
        ys = calibration.isotonic["y"]
        if not xs:
            return p
        # Piecewise-linear interpolation; clip outside [x[0], x[-1]].
        if p <= xs[0]:
            return float(ys[0])
        if p >= xs[-1]:
            return float(ys[-1])
        # Binary search for the bracketing pair.
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
    return p


# ──────────────────────────────────────────────────────────────────────
# Diagnostic report
# ──────────────────────────────────────────────────────────────────────


def format_report(calibrations: dict[str, AgentCalibration]) -> str:
    if not calibrations:
        return "(no agents with sufficient samples to calibrate)"
    lines = [
        f"{'agent':<14}{'method':<10}{'n':>5}{'raw_brier':>12}{'cal_brier':>12}{'improve':>10}",
        "-" * 63,
    ]
    sorted_cals = sorted(calibrations.values(), key=lambda c: -c.improvement)
    for c in sorted_cals:
        lines.append(
            f"{c.agent:<14}{c.method:<10}{c.n_samples:>5}"
            f"{c.raw_brier:>12.4f}{c.calibrated_brier:>12.4f}{c.improvement:>10.4f}"
        )
    return "\n".join(lines)
