from __future__ import annotations

from pantheon_core.schema import ApprovalToken, ExitConditions, Thesis

from strategos.orderbook import parse_book
from strategos.paper import PaperBook
from strategos.slippage import estimate_slippage, slippage_eats_edge


def _approval(size_pct: float = 0.03) -> ApprovalToken:
    return ApprovalToken(
        thesis_id="th1",
        decision="APPROVED",
        reason_code="OK",
        note="",
        final_size_pct=size_pct,
        kelly_fraction=0.10,
    )


def _thesis(direction: str = "YES") -> Thesis:
    return Thesis(
        thesis_id="th1",
        signal_id="sig",
        market_id="m1",
        question="?",
        direction=direction,
        council_probability=0.55,
        raw_market_probability=0.40,
        edge=0.15 if direction == "YES" else -0.15,
        confidence=0.75,
        recommended_size_pct=0.03,
        exit_conditions=ExitConditions(
            invalidation="x", target=0.55, stop=0.30, max_hold_days=30
        ),
    )


def test_estimate_slippage_zero_size():
    assert estimate_slippage(0, 1000) == 0.0


def test_estimate_slippage_capped():
    # Very large order vs tiny depth.
    slip = estimate_slippage(1_000_000, 100)
    assert slip == 0.05


def test_slippage_eats_edge():
    assert slippage_eats_edge(50_000, 100_000, edge=0.02)
    assert not slippage_eats_edge(1_000, 1_000_000, edge=0.10)


def test_parse_book_orders_levels():
    book = parse_book(
        {
            "bids": [
                {"price": "0.39", "size": "50"},
                {"price": "0.40", "size": "100"},
            ],
            "asks": [
                {"price": "0.43", "size": "100"},
                {"price": "0.42", "size": "200"},
            ],
        }
    )
    assert book.best_bid == 0.40
    assert book.best_ask == 0.42
    assert abs(book.spread - 0.02) < 1e-9


def test_paper_execute_yes_win():
    book = PaperBook(portfolio_usdc=10_000)
    trade = book.execute(_approval(0.03), _thesis("YES"), mid_price=0.40, depth_usdc=50_000)
    assert trade.status == "filled"
    assert trade.direction == "YES"
    pnl = book.settle(trade.trade_id, resolution_yes_price=1.0)
    assert pnl > 0


def test_paper_execute_yes_loss():
    book = PaperBook(portfolio_usdc=10_000)
    trade = book.execute(_approval(0.03), _thesis("YES"), mid_price=0.40, depth_usdc=50_000)
    pnl = book.settle(trade.trade_id, resolution_yes_price=0.0)
    assert pnl < 0


def test_paper_no_direction_uses_no_side_price():
    book = PaperBook(portfolio_usdc=10_000)
    trade = book.execute(_approval(0.03), _thesis("NO"), mid_price=0.40, depth_usdc=50_000)
    assert trade.direction == "NO"
    # Entry side price for NO = 1 - 0.40 = 0.60.
    assert abs(trade.entry_price - 0.60) < 1e-9
