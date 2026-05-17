"""Tests for the Circle developer-platform clients:
- USYC treasury (idle bankroll parking)
- Paymaster (USDC-denominated gas)
- Gateway (unified cross-chain balance)

All hermetic. Stub clients for the Paymaster + Gateway HTTP calls;
USYC treasury is pure math, no network.
"""

from __future__ import annotations


import pytest

from strategos.gateway_client import (
    GatewayBalance,
    GatewayClient,
)
from strategos.paymaster_client import (
    DEFAULT_USDC_PER_NATIVE,
    PaymasterClient,
    PaymasterQuote,
)
from strategos.usyc_treasury import (
    TreasuryState,
    daily_accrual,
    project_treasury_revenue,
)


# ─── USYC treasury (pure math) ────────────────────────────────────────


def test_treasury_idle_subtracts_parked():
    s = TreasuryState(book_usdc=10_000, parked_usdc=4_000)
    assert s.idle_usdc == 6_000


def test_treasury_mint_intent_holds_below_floor():
    s = TreasuryState(book_usdc=150, parked_usdc=0, min_unallocated_usdc=200)
    intent = s.mint_intent()
    assert intent.action == "hold"
    assert intent.amount_usdc == 0.0


def test_treasury_mint_intent_parks_above_floor():
    s = TreasuryState(book_usdc=10_000, parked_usdc=0, min_unallocated_usdc=100)
    intent = s.mint_intent()
    assert intent.action == "mint"
    # Idle 10_000 − floor 100 = 9_900 to park
    assert intent.amount_usdc == pytest.approx(9_900.0)


def test_treasury_redeem_intent_idle_covers_need():
    s = TreasuryState(book_usdc=10_000, parked_usdc=2_000)
    intent = s.redeem_intent(needed_usdc=500)
    assert intent.action == "hold"


def test_treasury_redeem_intent_shortfall_pulls_from_park():
    s = TreasuryState(book_usdc=10_000, parked_usdc=8_000)
    # idle = 2000, need 5000 → shortfall 3000
    intent = s.redeem_intent(needed_usdc=5_000)
    assert intent.action == "redeem"
    assert intent.amount_usdc == pytest.approx(3_000.0)


def test_treasury_redeem_caps_at_parked():
    s = TreasuryState(book_usdc=10_000, parked_usdc=1_000)
    # idle 9000, need 12000 → shortfall 3000, but only 1000 parked
    intent = s.redeem_intent(needed_usdc=12_000)
    assert intent.amount_usdc == pytest.approx(1_000.0)


def test_treasury_apply_mint_updates_parked():
    s = TreasuryState(book_usdc=10_000, parked_usdc=0)
    s.apply_mint(5_000)
    assert s.parked_usdc == 5_000


def test_treasury_apply_mint_clamps_to_idle():
    s = TreasuryState(book_usdc=1_000, parked_usdc=0)
    s.apply_mint(5_000)  # tries to park more than idle
    assert s.parked_usdc == 1_000


def test_treasury_apply_mint_rejects_negative():
    s = TreasuryState(book_usdc=1_000)
    with pytest.raises(ValueError):
        s.apply_mint(-100)


def test_daily_accrual_basic():
    # $10k × 5% APY / 365 = ~$1.37/day
    accrual = daily_accrual(10_000, yield_bps=500)
    assert accrual == pytest.approx(1.3699, abs=0.001)


def test_daily_accrual_zero_amount():
    assert daily_accrual(0, yield_bps=500) == 0.0


def test_project_treasury_revenue_annual():
    p = project_treasury_revenue(expected_idle_usdc=10_000, yield_bps=500, days=365)
    # $10k × 5% × 1yr = $500
    assert p["total_accrual_usdc"] == pytest.approx(500.0, abs=0.01)
    assert p["effective_apy"] == pytest.approx(0.05)


# ─── Paymaster ────────────────────────────────────────────────────────


class _StubResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _StubClient:
    def __init__(self, payloads, error=None):
        self._payloads = list(payloads)
        self._error = error
        self.calls = []

    async def get(self, url, *, params=None, headers=None, timeout=10.0):
        self.calls.append((url, params or {}, headers or {}))
        if self._error:
            raise self._error
        payload = self._payloads.pop(0) if self._payloads else {}
        return _StubResp(200, payload)


def test_paymaster_quote_usdc_arithmetic():
    """Quote: 21000 gas × 30 gwei = 630_000 gwei = 6.3e14 wei
    × 0.003 USDC/native = 1.89e-6 USDC × 1.005 markup = 1.8995e-6 USDC."""
    q = PaymasterQuote(usdc_per_native=0.003, markup_bps=50)
    usdc = q.quote_usdc(int(6.3e14))
    # native = 6.3e14 / 1e18 = 6.3e-4 native ETH
    # base = 6.3e-4 × 0.003 = 1.89e-6 USDC
    # marked up = × 1.005 = ~1.899e-6 USDC
    assert usdc == pytest.approx(1.899e-6, rel=0.01)


@pytest.mark.asyncio
async def test_paymaster_quote_falls_back_on_error():
    client = _StubClient([], error=RuntimeError("offline"))
    pm = PaymasterClient(client=client)
    q = await pm.quote()
    assert q.usdc_per_native == DEFAULT_USDC_PER_NATIVE


@pytest.mark.asyncio
async def test_paymaster_decide_paymaster_when_native_insufficient():
    client = _StubClient([{"usdcPerNative": 0.003, "markupBps": 50}])
    pm = PaymasterClient(client=client)
    intent = await pm.decide(
        estimated_native_wei=int(1e15),
        native_balance_wei=0,
        usdc_balance=1.0,
        prefer_usdc=False,
    )
    assert intent.mode == "paymaster_usdc"
    assert "insufficient native gas" in intent.reason


@pytest.mark.asyncio
async def test_paymaster_decide_paymaster_when_prefer_usdc():
    client = _StubClient([{"usdcPerNative": 0.003, "markupBps": 50}])
    pm = PaymasterClient(client=client)
    intent = await pm.decide(
        estimated_native_wei=int(1e15),
        native_balance_wei=int(1e18),  # plenty
        usdc_balance=10.0,
        prefer_usdc=True,
    )
    assert intent.mode == "paymaster_usdc"


@pytest.mark.asyncio
async def test_paymaster_decide_native_when_cheaper_and_available():
    client = _StubClient([{"usdcPerNative": 0.003, "markupBps": 50}])
    pm = PaymasterClient(client=client)
    intent = await pm.decide(
        estimated_native_wei=int(1e15),
        native_balance_wei=int(1e18),
        usdc_balance=10.0,
        prefer_usdc=False,
    )
    assert intent.mode == "native"


@pytest.mark.asyncio
async def test_paymaster_decide_paymaster_even_when_usdc_short():
    """Both empty → still route to paymaster so the operator sees the
    needed balance in the intent."""
    client = _StubClient([{"usdcPerNative": 0.003, "markupBps": 50}])
    pm = PaymasterClient(client=client)
    intent = await pm.decide(
        estimated_native_wei=int(1e15),
        native_balance_wei=0,
        usdc_balance=0.0,
        prefer_usdc=True,
    )
    assert intent.mode == "paymaster_usdc"
    assert "insufficient native + USDC" in intent.reason


# ─── Gateway ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gateway_balance_parses_response():
    payload = {
        "totalUSDC": 12_345.67,
        "perChain": {"arc": 5_000, "polygon": 4_345.67, "ethereum": 3_000},
    }
    client = _StubClient([payload])
    g = GatewayClient(client=client)
    b = await g.balance(address="0xabc")
    assert b.total_usdc == pytest.approx(12_345.67)
    assert b.per_chain["arc"] == 5_000


@pytest.mark.asyncio
async def test_gateway_balance_falls_back_to_zero_on_error():
    client = _StubClient([], error=RuntimeError("offline"))
    g = GatewayClient(client=client)
    b = await g.balance(address="0xabc")
    assert b.total_usdc == 0.0
    assert b.per_chain == {}


@pytest.mark.asyncio
async def test_gateway_unified_balance_returns_total():
    payload = {"totalUSDC": 7_500, "perChain": {"arc": 5_000, "polygon": 2_500}}
    client = _StubClient([payload])
    g = GatewayClient(client=client)
    total = await g.unified_balance("0xabc")
    assert total == pytest.approx(7_500)


def test_gateway_transfer_intent_drains_smallest_first():
    """Default: prefer smallest source chains first to consolidate liquidity."""
    g = GatewayClient(client=None)
    bal = GatewayBalance(
        total_usdc=10_000,
        per_chain={"arc": 6_000, "polygon": 2_000, "ethereum": 1_000, "base": 1_000},
        snapshot_at="2026-05-17T00:00Z",
    )
    intent = g.transfer_intent(balance=bal, target_chain="arc", amount_usdc=3_000)
    # Smallest first: base (1k) + ethereum (1k) + polygon (2k) covers 3k.
    assert "base" in intent.source_chains
    assert "ethereum" in intent.source_chains
    # arc itself should never be a source for an arc-targeted transfer.
    assert "arc" not in intent.source_chains


def test_gateway_transfer_intent_signals_insufficient():
    g = GatewayClient(client=None)
    bal = GatewayBalance(
        total_usdc=500,
        per_chain={"polygon": 500},
        snapshot_at="2026-05-17T00:00Z",
    )
    intent = g.transfer_intent(balance=bal, target_chain="arc", amount_usdc=10_000)
    assert "insufficient liquidity" in intent.reason


def test_gateway_transfer_intent_drains_largest_when_preferred():
    g = GatewayClient(client=None)
    bal = GatewayBalance(
        total_usdc=10_000,
        per_chain={"polygon": 4_000, "ethereum": 4_000, "base": 2_000},
        snapshot_at="2026-05-17T00:00Z",
    )
    intent = g.transfer_intent(
        balance=bal, target_chain="arc", amount_usdc=3_000, prefer_drain=True
    )
    # Largest-first: polygon (4k) covers the 3k need alone.
    assert intent.source_chains[0] in ("polygon", "ethereum")
