"""The Areopagus Court — final gatekeeper before a thesis becomes a trade.

The court does three things, in order:

1. ``evaluate_signal`` — cheap pre-deliberation gates so we never spend
   Claude tokens deliberating obviously-untradeable signals.
2. ``evaluate_thesis`` — full risk evaluation: vetos, confidence, portfolio
   exposure, half-Kelly sizing, post-resize portfolio re-check.
3. ``record_restraint`` — when we decline to trade, build a ProofOfRestraint
   so the on-chain ``NoTradeAlpha`` contract can witness the discipline.

The court is intentionally stateless w.r.t. Redis/DB: it consumes a
``PortfolioState`` snapshot supplied by the caller (the API gateway). That
keeps unit tests deterministic and prevents the court from racing with the
position monitor.
"""

from __future__ import annotations

import structlog

from pantheon_core.direction import entry_price as direction_entry_price
from pantheon_core.schema import ApprovalToken, RejectionRecord, Signal, Thesis

from areopagus.drawdown import apply_drawdown
from areopagus.gates import (
    GateResult,
    PortfolioState,
    check_signal_gates,
    check_thesis_gates,
)
from areopagus.kelly import DEFAULT_MIN_THRESHOLD as KELLY_MIN_FLOOR
from areopagus.kelly import size_position
from areopagus.proof_of_restraint import ProofOfRestraint

log = structlog.get_logger("areopagus.court")


class AreopagusCourt:
    def __init__(self, portfolio: PortfolioState | None = None) -> None:
        self.portfolio = portfolio or PortfolioState()

    def evaluate_signal(self, signal: Signal) -> GateResult:
        return check_signal_gates(signal)

    def evaluate_thesis(self, thesis: Thesis, signal: Signal) -> ApprovalToken | RejectionRecord:
        gate = check_thesis_gates(thesis, self.portfolio, signal)
        if not gate.passed:
            log.info(
                "areopagus.thesis_rejected",
                thesis_id=thesis.thesis_id,
                reason=gate.reason_code,
            )
            return RejectionRecord(
                thesis_id=thesis.thesis_id,
                reason_code=gate.reason_code,
                note=gate.note,
            )

        # Use direction-aware edge and price so YES/NO trades size symmetrically.
        directional_edge = abs(thesis.signed_edge)
        price = direction_entry_price(thesis.raw_market_probability, thesis.direction)

        final_size, kelly_frac, size_reason = size_position(
            directional_edge=directional_edge,
            entry_price=price,
        )

        # Drawdown-aware down-scaling. If the book has been marked-to-market
        # against a peak and is currently below it, multiply the half-Kelly
        # result by a floor-clamped ramp (see areopagus.drawdown). Skipped if
        # peak_equity is unset (zero) — callers that don't track equity get
        # the existing behaviour.
        dd_multiplier = 1.0
        if self.portfolio.peak_equity > 0 and final_size > 0:
            final_size, dd_multiplier = apply_drawdown(
                final_size,
                current_equity=self.portfolio.current_equity,
                peak_equity=self.portfolio.peak_equity,
            )
            # Re-check minimum floor after DD haircut.
            if final_size > 0 and final_size < KELLY_MIN_FLOOR:
                return RejectionRecord(
                    thesis_id=thesis.thesis_id,
                    reason_code="DRAWDOWN_FLOOR",
                    note=(
                        f"drawdown haircut ({dd_multiplier:.2f}x) pushed sizing "
                        f"below floor {KELLY_MIN_FLOOR}"
                    ),
                )

        if size_reason in ("sub_threshold", "no_edge"):
            log.info(
                "areopagus.thesis_below_floor",
                thesis_id=thesis.thesis_id,
                size_reason=size_reason,
            )
            return RejectionRecord(
                thesis_id=thesis.thesis_id,
                reason_code="SUB_THRESHOLD_KELLY" if size_reason == "sub_threshold" else "NO_EDGE",
                note=f"half-Kelly {kelly_frac * 0.5:.4f} insufficient ({size_reason})",
            )

        # Re-check portfolio exposure against the *final* size, not the council's recommendation.
        post_gate = check_thesis_gates(thesis, self.portfolio, signal, proposed_size_pct=final_size)
        if not post_gate.passed:
            return RejectionRecord(
                thesis_id=thesis.thesis_id,
                reason_code=post_gate.reason_code,
                note=f"post-Kelly: {post_gate.note}",
            )

        decision = "RESIZED" if size_reason == "capped" or dd_multiplier < 1.0 else "APPROVED"
        note = f"half-Kelly sizing: {final_size:.2%}"
        if size_reason == "capped":
            note += " (capped at MAX_POSITION_PCT)"
        if dd_multiplier < 1.0:
            note += f" | drawdown haircut: {dd_multiplier:.2f}x"
        if thesis.cassandra_flags:
            note += f" | cassandra: {', '.join(thesis.cassandra_flags)}"
        if thesis.humans_flags:
            note += f" | humans: {', '.join(thesis.humans_flags)}"

        return ApprovalToken(
            thesis_id=thesis.thesis_id,
            decision=decision,  # type: ignore[arg-type]
            reason_code="OK",
            note=note,
            final_size_pct=final_size,
            kelly_fraction=kelly_frac,
        )

    def record_restraint(
        self,
        signal: Signal,
        signal_json: str,
        rejection: RejectionRecord,
    ) -> ProofOfRestraint:
        """Build the on-chain proof-of-restraint payload for this rejection."""
        return ProofOfRestraint.create(
            signal_id=signal.signal_id,
            market_id=signal.market_id,
            signal_json=signal_json,
            reason_code=rejection.reason_code,
            note=rejection.note,
        )
