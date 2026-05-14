"""Hard risk gates enforced by Areopagus.

Every limit here corresponds to a clause in ``docs/RISK_POLICY.md``. Soft
limits (``MAX_*`` without ``_HARD``) reject the signal but record it as a
warning-class rejection — useful for ProofOfRestraint telemetry. Hard limits
(``*_HARD``) indicate something is so out of policy that we want a louder
signal upstream.

Order of evaluation matters: the cheapest, most-objective gates run first so
we surface "obvious" violations before invoking the council.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pantheon_core.schema import Signal, Thesis

# ---- Signal-level limits ---------------------------------------------------
MIN_EDGE = 0.05            # |edge| in probability space
MIN_LIQUIDITY = 0.50
MAX_SPREAD = 0.08
MAX_SPREAD_HARD = 0.12
MIN_DAYS = 2.0
MAX_DAYS = 90.0
MAX_STALENESS = 300        # seconds
MAX_STALENESS_HARD = 600

# ---- Thesis / portfolio-level limits --------------------------------------
MIN_CONFIDENCE = 0.65
MAX_POSITION_PCT = 0.05
MAX_POSITION_HARD = 0.10
MAX_OPEN_POSITIONS = 10
MAX_TOTAL_EXPOSURE = 0.40
MAX_CATEGORY_EXPOSURE = 0.15
MIN_POSITION_THRESHOLD = 0.005


@dataclass
class PortfolioState:
    """Snapshot of the live portfolio fed into Areopagus on every evaluation."""

    open_positions: int = 0
    total_exposure: float = 0.0
    category_exposure: dict[str, float] = field(default_factory=dict)
    drawdown_pause: bool = False
    daily_drawdown: float = 0.0
    weekly_drawdown: float = 0.0


@dataclass
class GateResult:
    passed: bool
    reason_code: str
    note: str


def check_signal_gates(signal: Signal) -> GateResult:
    """Pre-deliberation signal gates."""
    if signal.staleness_seconds > MAX_STALENESS_HARD:
        return GateResult(
            False,
            "STALENESS_HARD",
            f"staleness {signal.staleness_seconds}s > {MAX_STALENESS_HARD}s hard limit",
        )
    if signal.staleness_seconds > MAX_STALENESS:
        return GateResult(
            False,
            "STALENESS",
            f"staleness {signal.staleness_seconds}s > {MAX_STALENESS}s",
        )
    if signal.spread > MAX_SPREAD_HARD:
        return GateResult(
            False,
            "SPREAD_HARD",
            f"spread {signal.spread:.2%} > {MAX_SPREAD_HARD:.0%} hard limit",
        )
    if signal.spread > MAX_SPREAD:
        return GateResult(
            False,
            "SPREAD",
            f"spread {signal.spread:.2%} > {MAX_SPREAD:.0%}",
        )
    if signal.liquidity_score < MIN_LIQUIDITY:
        return GateResult(
            False,
            "LIQUIDITY",
            f"liquidity_score {signal.liquidity_score:.3f} < {MIN_LIQUIDITY}",
        )
    if signal.edge_abs < MIN_EDGE:
        return GateResult(
            False,
            "EDGE",
            f"|edge| {signal.edge_abs:.3f} < {MIN_EDGE}",
        )
    if signal.days_to_resolution is not None:
        if signal.days_to_resolution < MIN_DAYS:
            return GateResult(
                False,
                "DAYS_TOO_CLOSE",
                f"days_to_resolution {signal.days_to_resolution:.1f} < {MIN_DAYS}",
            )
        if signal.days_to_resolution > MAX_DAYS:
            return GateResult(
                False,
                "DAYS_TOO_FAR",
                f"days_to_resolution {signal.days_to_resolution:.1f} > {MAX_DAYS}",
            )
    return GateResult(True, "OK", "signal gates passed")


def check_thesis_gates(
    thesis: Thesis,
    portfolio: PortfolioState,
    signal: Signal,
    *,
    proposed_size_pct: float | None = None,
) -> GateResult:
    """Post-deliberation thesis gates.

    ``proposed_size_pct`` overrides ``thesis.recommended_size_pct`` so the
    court can re-check portfolio exposure against the *post-Kelly* size.
    """
    if thesis.zeus_veto:
        return GateResult(False, "ZEUS_VETO", "Zeus cast constitutional veto")
    if thesis.solon_veto:
        return GateResult(False, "SOLON_VETO", "Solon cast compliance veto")
    if thesis.confidence < MIN_CONFIDENCE:
        return GateResult(
            False,
            "LOW_CONFIDENCE",
            f"council confidence {thesis.confidence:.2f} < {MIN_CONFIDENCE}",
        )
    if portfolio.drawdown_pause:
        return GateResult(
            False,
            "DRAWDOWN_PAUSE",
            f"daily drawdown pause active ({portfolio.daily_drawdown:.1%})",
        )
    if portfolio.open_positions >= MAX_OPEN_POSITIONS:
        return GateResult(
            False,
            "MAX_POSITIONS",
            f"open positions {portfolio.open_positions} >= {MAX_OPEN_POSITIONS}",
        )

    size = proposed_size_pct if proposed_size_pct is not None else thesis.recommended_size_pct
    if size > MAX_POSITION_HARD:
        return GateResult(
            False,
            "POSITION_HARD",
            f"proposed size {size:.2%} > hard cap {MAX_POSITION_HARD:.0%}",
        )

    cat_exp = portfolio.category_exposure.get(signal.category, 0.0)
    if cat_exp + size > MAX_CATEGORY_EXPOSURE:
        return GateResult(
            False,
            "CATEGORY_EXPOSURE",
            f"category {signal.category} exposure {cat_exp:.2%}+{size:.2%} would exceed {MAX_CATEGORY_EXPOSURE:.0%}",
        )
    if portfolio.total_exposure + size > MAX_TOTAL_EXPOSURE:
        return GateResult(
            False,
            "TOTAL_EXPOSURE",
            f"total exposure {portfolio.total_exposure:.2%}+{size:.2%} would exceed {MAX_TOTAL_EXPOSURE:.0%}",
        )

    return GateResult(True, "OK", "thesis gates passed")
