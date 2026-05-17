"""Beta calibration (Kull, Silva-Filho, Flach 2017).

Companion to ``agent_calibration.py`` which fits Platt + isotonic. Beta
calibration is a *parametric* alternative whose family contains the
identity function as a special case — meaning a well-calibrated model
is left alone, whereas Platt scaling will *distort* a calibrated
model because the sigmoid family does not contain the identity.

Reference paper:
  Kull, Silva-Filho, Flach (2017), "Beta calibration: a well-founded
  and easily implemented improvement on logistic calibration for
  binary classifiers". AISTATS 2017.

Implementation is the standard reduction: fit a two-feature logistic
regression on ``[log(s), log(1-s)]`` of the raw score ``s`` with the
binary outcome. The resulting linear-in-logits model maps to the beta
calibration formula

    g(s) = 1 / (1 + exp(-(a*log(s) - b*log(1-s) + c)))

with a >= 0, b >= 0 (enforced post-fit by reflection / inversion).

We expose the same surface as ``AgentCalibration``: ``calibrate_from_csv``,
the diagnostic dataclass, plus ``apply_beta`` for runtime use by
``boule.calibrator``.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

# Sklearn LogisticRegression is the only fit dependency. Kept lazy so
# import-time cost is zero for callers that only need ``apply_beta``.

EPS = 1e-6


@dataclass
class BetaCalibration:
    """Per-agent fitted beta calibration parameters."""

    agent: str
    n_samples: int
    raw_brier: float
    calibrated_brier: float
    improvement: float
    # Beta has three serialised params: a, b, c. Identity is (1, 1, 0).
    a: float
    b: float
    c: float
    # If the fit didn't beat identity on held-out Brier, the runtime
    # short-circuits to the identity transform.
    method: str = "beta"


def _logit(s: np.ndarray) -> np.ndarray:
    s = np.clip(s, EPS, 1.0 - EPS)
    return np.log(s) - np.log(1.0 - s)


def _beta_features(s: np.ndarray) -> np.ndarray:
    """[log(s), -log(1-s)] feature pair used by the linear reduction.

    Note the negative sign on log(1-s) — this is the form that yields
    the canonical beta-calibration g(s) when the two logistic
    coefficients are read back as (a, b).
    """
    s = np.clip(s, EPS, 1.0 - EPS)
    return np.column_stack([np.log(s), -np.log(1.0 - s)])


def fit_beta(raw_scores: np.ndarray, outcomes: np.ndarray) -> tuple[float, float, float]:
    """Return ``(a, b, c)`` such that g(s) = sigmoid(a*log(s) - b*log(1-s) + c).

    Fitted by logistic regression on the two-feature reduction. The
    paper's enforcement (a >= 0, b >= 0) is handled by sklearn's
    bounded penalty for typical near-monotonic data; in pathological
    sign-flipped cases we clamp post-hoc.
    """
    from sklearn.linear_model import LogisticRegression

    X = _beta_features(raw_scores)
    clf = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    clf.fit(X, outcomes.astype(int))
    a, b = clf.coef_[0]
    c = float(clf.intercept_[0])
    # Beta calibration requires a,b >= 0 for monotonicity. The paper
    # handles negatives by reflecting; for our use case we clamp at 0
    # which is equivalent to dropping the bad coefficient.
    a = max(0.0, float(a))
    b = max(0.0, float(b))
    return a, b, c


def apply_beta(score: float, a: float, b: float, c: float) -> float:
    """Apply a fitted beta calibration to a single raw probability.

    Pure-Python, no numpy — designed to be hot-path-safe for the
    consumer in ``boule.calibrator``. ``score`` is the raw agent
    probability in (0, 1).
    """
    s = max(EPS, min(1.0 - EPS, float(score)))
    z = a * math.log(s) - b * math.log(1.0 - s) + c
    # Numerically-safe sigmoid.
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def brier(probs: np.ndarray, outcomes: np.ndarray) -> float:
    return float(np.mean((probs - outcomes) ** 2))


def calibrate_one(
    raw: list[tuple[float, int]],
) -> tuple[float, float, float, float, float]:
    """Cross-validated fit. Returns ``(a, b, c, raw_brier, calibrated_brier)``.

    Uses a simple 5-fold split. Falls back to identity ``(1, 1, 0)`` if
    the calibrated Brier is not strictly better than identity.
    """
    raw_scores = np.array([p for p, _ in raw], dtype=float)
    outcomes = np.array([o for _, o in raw], dtype=int)

    # Baseline Brier with no calibration.
    raw_brier = brier(raw_scores, outcomes)

    # 5-fold CV — fit on 4/5, score on 1/5, average.
    from sklearn.model_selection import KFold

    n = len(raw)
    n_splits = min(5, max(2, n // 5))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_briers: list[float] = []
    for train_idx, test_idx in kf.split(raw_scores):
        a, b, c = fit_beta(raw_scores[train_idx], outcomes[train_idx])
        preds = np.array([apply_beta(s, a, b, c) for s in raw_scores[test_idx]])
        cv_briers.append(brier(preds, outcomes[test_idx]))
    cal_brier = float(np.mean(cv_briers))

    # Final fit on the full sample.
    a, b, c = fit_beta(raw_scores, outcomes)

    # Identity-fallback: if calibration doesn't strictly beat the raw,
    # report identity params so the runtime is a no-op.
    if cal_brier >= raw_brier:
        return 1.0, 1.0, 0.0, raw_brier, raw_brier

    return a, b, c, raw_brier, cal_brier


def calibrate_from_csv(path: Path) -> dict[str, BetaCalibration]:
    """Fit a beta calibrator per agent from a backtest CSV.

    Same column convention as ``agent_calibration.calibrate_from_csv``:

        market_id,agent,vote,probability_estimate,confidence,brier,outcome

    where ``outcome`` is 0/1 for the realised YES/NO.
    """
    grouped: dict[str, list[tuple[float, int]]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            agent = row.get("agent")
            if not agent:
                continue
            try:
                p = float(row["probability_estimate"])
                o = int(float(row.get("outcome", "0")))
            except (KeyError, ValueError, TypeError):
                continue
            grouped.setdefault(agent, []).append((p, o))

    out: dict[str, BetaCalibration] = {}
    for agent, pairs in grouped.items():
        if len(pairs) < 10:
            continue
        a, b, c, raw_b, cal_b = calibrate_one(pairs)
        out[agent] = BetaCalibration(
            agent=agent,
            n_samples=len(pairs),
            raw_brier=raw_b,
            calibrated_brier=cal_b,
            improvement=raw_b - cal_b,
            a=a,
            b=b,
            c=c,
        )
    return out


def save_calibrations(cals: dict[str, BetaCalibration], path: Path) -> None:
    """Serialise to the same JSON shape ``boule.calibrator`` consumes for
    Platt — caller picks which calibration file to load.
    """
    payload = {
        "method": "beta",
        "fitted_at": _now_iso(),
        "agents": {k: asdict(v) for k, v in cals.items()},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
