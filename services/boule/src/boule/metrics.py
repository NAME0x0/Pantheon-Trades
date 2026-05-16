"""Prometheus metrics for the Pantheon council.

Lazy registration — if ``prometheus_client`` is installed we register
real metrics; otherwise every helper degrades to a no-op so the
service never crashes for a missing optional dep.

What we expose (intent — actual emission lives in the services that
import this module):

  - ``pantheon_deliberations_total{status}``      counter
  - ``pantheon_deliberation_duration_seconds``    histogram
  - ``pantheon_llm_cost_usd_total{provider}``     counter
  - ``pantheon_llm_calls_total{provider, model}`` counter
  - ``pantheon_restraint_witnesses_total``        counter
  - ``pantheon_drift_events_total``               counter
  - ``pantheon_council_diversity``                gauge (0..1)
  - ``pantheon_open_positions``                   gauge
  - ``pantheon_paper_equity_usdc``                gauge

The HTTP exporter binds to ``METRICS_PORT`` (default 9464) on first
``start_metrics_server()`` call; subsequent calls are idempotent.
"""

from __future__ import annotations

import os
from typing import Optional

import structlog

log = structlog.get_logger("boule.metrics")

METRICS_PORT = int(os.environ.get("METRICS_PORT", "9464"))


try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        start_http_server,
    )
    _ENABLED = True
except ImportError:  # pragma: no cover — dep is optional
    _ENABLED = False
    CollectorRegistry = None  # type: ignore[assignment]

_started = False


# ── Metric registry ─────────────────────────────────────────────────


class _NoOp:
    def labels(self, *_a, **_kw) -> "_NoOp":
        return self

    def inc(self, *_a, **_kw) -> None:
        pass

    def set(self, *_a, **_kw) -> None:
        pass

    def observe(self, *_a, **_kw) -> None:
        pass


def _make_metrics() -> dict:
    if not _ENABLED:
        return {k: _NoOp() for k in _METRIC_NAMES}

    return {
        "deliberations_total": Counter(
            "pantheon_deliberations_total",
            "Total council deliberations by terminal status",
            ["status"],
        ),
        "deliberation_duration_seconds": Histogram(
            "pantheon_deliberation_duration_seconds",
            "Wall-clock seconds per deliberation",
            buckets=(1, 2, 5, 10, 30, 60, 120, 300, 600),
        ),
        "llm_cost_usd_total": Counter(
            "pantheon_llm_cost_usd_total",
            "Cumulative LLM spend in USD",
            ["provider"],
        ),
        "llm_calls_total": Counter(
            "pantheon_llm_calls_total",
            "Number of completion calls",
            ["provider", "model"],
        ),
        "restraint_witnesses_total": Counter(
            "pantheon_restraint_witnesses_total",
            "ProofOfRestraint anchor events emitted",
        ),
        "drift_events_total": Counter(
            "pantheon_drift_events_total",
            "Model fingerprint drift detections",
        ),
        "council_diversity": Gauge(
            "pantheon_council_diversity",
            "Most recent diversity composite (0=collapse, 1=max)",
        ),
        "open_positions": Gauge(
            "pantheon_open_positions",
            "Open paper / live positions",
        ),
        "paper_equity_usdc": Gauge(
            "pantheon_paper_equity_usdc",
            "Strategos paper book equity in USDC",
        ),
    }


_METRIC_NAMES = (
    "deliberations_total",
    "deliberation_duration_seconds",
    "llm_cost_usd_total",
    "llm_calls_total",
    "restraint_witnesses_total",
    "drift_events_total",
    "council_diversity",
    "open_positions",
    "paper_equity_usdc",
)


m = _make_metrics()


def start_metrics_server(port: Optional[int] = None) -> None:
    """Bring up the Prometheus HTTP exporter on ``port``. Idempotent."""
    global _started
    if _started or not _ENABLED:
        return
    bind = port if port is not None else METRICS_PORT
    try:
        start_http_server(bind)
        _started = True
        log.info("boule.metrics.exporter_listening", port=bind)
    except Exception as e:  # noqa: BLE001
        log.warning("boule.metrics.exporter_failed", port=bind, error=str(e))


def is_enabled() -> bool:
    return _ENABLED
