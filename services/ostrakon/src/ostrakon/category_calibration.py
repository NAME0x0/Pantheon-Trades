"""Per-category calibration — refit Platt / isotonic / beta per market category.

Original ``agent_calibration`` fits one global calibrator per agent.
Empirically prediction-market outcomes are not category-homogeneous:

  - Politics has fat-tailed base rates near 0.0 / 1.0 (resignations,
    convictions) and is poorly served by a sigmoid.
  - Crypto is volatile + reflexive; recent-window weighting matters.
  - Sports is closest to base-rate-flat and benefits from isotonic.
  - Macro is autocorrelated; the same Fed pattern recurs across cycles.

This module wraps the existing calibrators (Platt/isotonic/beta) and
partitions the calibration sample by ``category``, fitting a per-
category model and falling back to the global model when a category
is too thin to fit alone.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import json

Category = Literal["crypto", "politics", "sports", "science", "other"]
DEFAULT_CATEGORIES: tuple[Category, ...] = (
    "crypto", "politics", "sports", "science", "other",
)

# Minimum sample size per category before we fit alone — otherwise
# the category inherits the global calibrator.
MIN_PER_CATEGORY = 30


@dataclass
class CategoryCalibration:
    """One fitted calibrator per (agent, category) pair plus the global
    fallback. ``method`` is one of "platt", "isotonic", "beta",
    "identity". Each per-category entry carries its sample count."""

    agent: str
    method: Literal["platt", "isotonic", "beta", "identity"]
    global_params: dict[str, Any]
    per_category: dict[str, dict[str, Any]] = field(default_factory=dict)
    sample_counts: dict[str, int] = field(default_factory=dict)


def _platt_params(probs, outcomes) -> dict[str, float]:
    """Tiny Platt fit — logistic of one variable."""
    from sklearn.linear_model import LogisticRegression
    import numpy as np

    arr = np.array(probs, dtype=float).reshape(-1, 1)
    out = np.array(outcomes, dtype=int)
    clf = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    clf.fit(arr, out)
    return {
        "slope": float(clf.coef_[0][0]),
        "intercept": float(clf.intercept_[0]),
    }


def apply_platt(raw: float, params: dict[str, Any]) -> float:
    """Apply a fitted Platt model to a single raw probability."""
    import math

    slope = float(params.get("slope", 1.0))
    intercept = float(params.get("intercept", 0.0))
    z = slope * raw + intercept
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def fit_per_category(
    samples: list[dict[str, Any]],
    *,
    method: Literal["platt"] = "platt",
    min_per_category: int = MIN_PER_CATEGORY,
) -> dict[str, CategoryCalibration]:
    """Fit per-agent per-category calibrators from a backtest sample.

    ``samples`` is a list of
    ``{agent, category, probability_estimate, outcome}`` dicts.

    Returns a dict keyed by agent name, where each entry has a global
    Platt fit + a per-category dict for categories meeting the
    minimum-sample threshold.
    """
    if method != "platt":
        # Beta / isotonic per-category extend by analogy; we ship Platt
        # first because it's the most robust on small per-category
        # samples (≤ 100).
        raise NotImplementedError(f"method {method!r} not yet supported per-category")

    # Bucket samples by agent, then by category within agent.
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        agent = s.get("agent")
        if agent:
            by_agent[agent].append(s)

    out: dict[str, CategoryCalibration] = {}
    for agent, rows in by_agent.items():
        if len(rows) < 10:
            continue
        global_probs = [float(r["probability_estimate"]) for r in rows]
        global_outcomes = [int(r["outcome"]) for r in rows]
        try:
            global_params = _platt_params(global_probs, global_outcomes)
        except Exception:
            global_params = {"slope": 1.0, "intercept": 0.0}

        per_cat: dict[str, dict[str, Any]] = {}
        counts: dict[str, int] = {}
        by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            cat = str(r.get("category", "other")).lower()
            by_cat[cat].append(r)
        for cat, cat_rows in by_cat.items():
            counts[cat] = len(cat_rows)
            if len(cat_rows) < min_per_category:
                continue
            cat_probs = [float(r["probability_estimate"]) for r in cat_rows]
            cat_outcomes = [int(r["outcome"]) for r in cat_rows]
            try:
                per_cat[cat] = _platt_params(cat_probs, cat_outcomes)
            except Exception:
                continue

        out[agent] = CategoryCalibration(
            agent=agent,
            method="platt",
            global_params=global_params,
            per_category=per_cat,
            sample_counts=counts,
        )
    return out


def apply_calibration(
    raw_prob: float,
    *,
    agent: str,
    category: str,
    calibrations: dict[str, CategoryCalibration],
) -> float:
    """Apply the right calibrator for ``(agent, category)`` to one
    raw probability. Falls back to global → identity.
    """
    cal = calibrations.get(agent)
    if cal is None:
        return raw_prob
    cat_key = (category or "other").lower()
    params = cal.per_category.get(cat_key) or cal.global_params
    if cal.method == "platt":
        return apply_platt(raw_prob, params)
    # Other methods would dispatch here; for now Platt only.
    return raw_prob


def save_calibrations(
    cals: dict[str, CategoryCalibration],
    path: Path,
) -> None:
    """JSON serialise the fitted calibrators for runtime consumption."""
    from datetime import datetime, timezone
    payload = {
        "fitted_at": datetime.now(timezone.utc).isoformat(),
        "agents": {
            k: {
                "agent": v.agent,
                "method": v.method,
                "global_params": v.global_params,
                "per_category": v.per_category,
                "sample_counts": v.sample_counts,
            }
            for k, v in cals.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
