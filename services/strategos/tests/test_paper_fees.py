"""Tests for slippage + fee + half-spread realism in the paper book."""

from __future__ import annotations

import pytest

from pantheon_core.schema import (
    ApprovalToken,
    ExitConditions,
    Thesis,
)
from strategos.paper import PaperBook


def _token() -> ApprovalToken:
    return ApprovalToken(
        thesis_id="th-1",
        decision="RESIZED",
        reason_code="OK",
        note="",
        final_size_pct=0.05,
        kelly_fraction=0.375,
    )


def _thesis(direction: str = "YES") -> Thesis:
    return Thesis(
        thesis_id="th-1",
        signal_id="sig-1",
        market_id="0xtest",
        question="x?",
        direction=direction,  # type: ignore[arg-type]
        council_probability=0.6,
        raw_market_probability=0.42,
        edge=0.18 if direction == "YES" else -0.18,
        confidence=0.7,
        recommended_size_pct=0.05,
        exit_conditions=ExitConditions(
            invalidation="n/a", target=0.7, stop=0.37, max_hold_days=30
        ),
        agents=[],
        vote_summary={"APPROVE": 8, "REJECT": 0, "ABSTAIN": 2},
        weighted_approval=0.8,
        zeus_veto=False,
        solon_veto=False,
        trace_id="trace-1",
        debate_blocks=[],
        status="pending_areopagus",
    )


def test_yes_fill_uses_ask_when_supplied():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=0)
    trade = book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=50_000,
        bid=0.41,
        ask=0.43,
    )
    # Fill ≥ ask (slippage may push it higher, never lower than the inside).
    assert trade.fill_price >= 0.43


def test_yes_fill_falls_back_to_mid_plus_half_spread():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=0)
    trade = book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=50_000,
    )
    # No bid/ask supplied → uses mid + DEFAULT_HALF_SPREAD = 0.43+ slippage.
    assert trade.fill_price > 0.42


def test_no_direction_uses_yes_bid_inversion():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=0)
    trade = book.execute(
        token=_token(),
        thesis=_thesis("NO"),
        mid_price=0.42,
        depth_usdc=50_000,
        bid=0.41,
        ask=0.43,
    )
    # NO buyer pays (1 - bid) = 0.59+ slippage.
    assert trade.fill_price >= 0.59


def test_entry_fee_charged_on_notional():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=200)  # 2%
    book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=50_000,
        bid=0.41,
        ask=0.43,
    )
    # 5% of 10k notional × 2% fee = $10 entry fee.
    assert abs(book.fees_paid_usdc - 10.0) < 0.01


def test_settlement_winner_pnl_includes_exit_fee():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=200)
    trade = book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=1_000_000,  # huge depth → negligible slippage
        bid=0.41,
        ask=0.43,
    )
    pnl = book.settle(trade.trade_id, resolution_yes_price=1.0)
    # Without fees, contracts ≈ 500/0.43 ≈ 1162. Win pays (1 - 0.43) per
    # contract = 0.57 × 1162 ≈ 662. Exit fee = 2% of 1162 ≈ 23.24.
    # Net pnl ≈ 662 - 23.24 ≈ 638.76. Allow 1% wiggle for slippage.
    assert 630 <= pnl <= 670


def test_settlement_loser_pnl_negative_and_no_exit_fee():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=200)
    trade = book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=1_000_000,
        bid=0.41,
        ask=0.43,
    )
    fees_before = book.fees_paid_usdc
    pnl = book.settle(trade.trade_id, resolution_yes_price=0.0)
    # Losing leg: contracts × (0 - fill_price) = full loss of notional.
    assert pnl < 0
    # No exit fee on a zero payout (rounding-zero contribution).
    assert book.fees_paid_usdc - fees_before < 0.01


def test_max_take_fraction_caps_order_size():
    book = PaperBook(portfolio_usdc=10_000.0, fee_bps=0)
    # 5% of 10k = $500; depth $2,000 → 25% take → caps to MAX_TAKE_FRACTION (10%).
    trade = book.execute(
        token=_token(),
        thesis=_thesis("YES"),
        mid_price=0.42,
        depth_usdc=2_000,
        bid=0.41,
        ask=0.43,
    )
    assert trade.status == "partial"
    assert trade.size_usdc == pytest.approx(200.0, rel=0.01)
