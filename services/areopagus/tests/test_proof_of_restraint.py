"""Tests for ProofOfRestraint payload + on-chain writer wiring.

The chain writer itself is tested with an injected fake web3 contract so
no network is required.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace


from areopagus.chain import PROOF_OF_RESTRAINT_ABI, RestraintChainWriter
from areopagus.proof_of_restraint import ProofOfRestraint


def _proof() -> ProofOfRestraint:
    return ProofOfRestraint.create(
        signal_id="sig-001",
        market_id="0xpantheon_test",
        signal_json='{"market_id":"0xpantheon_test","oracle_probability":0.59}',
        reason_code="ZEUS_VETO",
        note="cluster correlation violation",
    )


def test_create_hashes_signal_payload():
    p = _proof()
    assert p.signal_hash.startswith("0x")
    assert len(p.signal_hash) == 66  # 0x + 32 bytes hex


def test_to_calldata_matches_contract_signature():
    p = _proof()
    calldata = p.to_calldata()
    # Must be exactly the four declineTrade arguments.
    assert set(calldata.keys()) == {"signalHash", "marketId", "reasonCode", "note"}
    assert calldata["signalHash"] == p.signal_hash
    assert calldata["marketId"] == "0xpantheon_test"
    assert calldata["reasonCode"] == "ZEUS_VETO"
    assert calldata["note"] == "cluster correlation violation"


def test_abi_includes_decline_trade():
    fns = {entry["name"] for entry in PROOF_OF_RESTRAINT_ABI if entry["type"] == "function"}
    assert "declineTrade" in fns
    decline = next(e for e in PROOF_OF_RESTRAINT_ABI if e.get("name") == "declineTrade")
    arg_types = [inp["type"] for inp in decline["inputs"]]
    assert arg_types == ["bytes32", "string", "string", "string"]


def test_from_env_requires_address(monkeypatch):
    monkeypatch.delenv("PROOF_OF_RESTRAINT_ADDRESS", raising=False)
    monkeypatch.setenv("RPC_URL", "https://rpc.testnet.arc.network")
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "11" * 32)
    assert RestraintChainWriter.from_env() is None


def test_from_env_requires_rpc(monkeypatch):
    monkeypatch.setenv("PROOF_OF_RESTRAINT_ADDRESS", "0x" + "ab" * 20)
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "11" * 32)
    assert RestraintChainWriter.from_env() is None


def test_from_env_requires_private_key(monkeypatch):
    monkeypatch.setenv("PROOF_OF_RESTRAINT_ADDRESS", "0x" + "ab" * 20)
    monkeypatch.setenv("RPC_URL", "https://rpc.testnet.arc.network")
    monkeypatch.setenv("PRIVATE_KEY", "")
    assert RestraintChainWriter.from_env() is None


def test_from_env_builds_writer(monkeypatch):
    monkeypatch.setenv("PROOF_OF_RESTRAINT_ADDRESS", "0x" + "ab" * 20)
    monkeypatch.setenv("RPC_URL", "https://rpc.testnet.arc.network")
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("CHAIN_ID", "5042002")
    writer = RestraintChainWriter.from_env()
    assert writer is not None
    assert writer._chain_id == 5042002


def test_write_rejects_bad_signal_hash(monkeypatch):
    """A signal_hash that doesn't decode to 32 bytes must be skipped, not raised."""

    class _FakeAccount:
        address = "0x" + "ab" * 20

        def sign_transaction(self, tx):  # pragma: no cover — never reached
            raise RuntimeError("should not sign on bad hash")

    writer = RestraintChainWriter(
        rpc_url="http://localhost",
        contract_address="0x" + "ab" * 20,
        private_key="0x" + "11" * 32,
        chain_id=5042002,
    )
    # Pre-populate so _ensure_client is a no-op.
    writer._w3 = SimpleNamespace()
    writer._account = _FakeAccount()
    writer._contract = SimpleNamespace()

    p = _proof()
    p.signal_hash = "0xdeadbeef"  # only 4 bytes, not 32

    result = asyncio.run(writer.write(p))
    assert result is None


def test_write_returns_none_on_rpc_failure(monkeypatch):
    """When the network call raises, write() must swallow and log, never raise."""

    class _BoomEth:
        async def get_transaction_count(self, *_a, **_kw):
            raise ConnectionError("rpc unreachable")

    class _BoomW3:
        eth = _BoomEth()
        provider = SimpleNamespace(disconnect=lambda: None)

        def to_checksum_address(self, x):
            return x

    writer = RestraintChainWriter(
        rpc_url="http://localhost",
        contract_address="0x" + "ab" * 20,
        private_key="0x" + "11" * 32,
        chain_id=5042002,
    )
    writer._w3 = _BoomW3()
    writer._contract = SimpleNamespace()
    writer._account = SimpleNamespace(address="0x" + "ab" * 20)

    result = asyncio.run(writer.write(_proof()))
    assert result is None  # Failure is swallowed, not propagated.
