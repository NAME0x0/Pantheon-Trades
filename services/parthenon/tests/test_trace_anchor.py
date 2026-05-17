"""Tests for the Arc-anchorable trace bundle.

Covers bundle determinism, hash equality across identical inputs,
metadata extraction, anchor payload projection, verify round-trip,
and graceful handling of pydantic / dict / dataclass event sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from parthenon.trace_anchor import (
    bundle_to_json,
    build_bundle,
    to_anchor_payload,
    verify_bundle,
)


def _ev(**kw):
    """Build a TraceEvent-shaped dict for tests."""
    base = {
        "trace_id": "trace-1",
        "event_id": kw.get("event_id", "ev-1"),
        "thesis_id": "thesis-1",
        "signal_id": "sig-1",
        "market_id": "0xmarket",
        "event_type": "agent_output",
        "agent": "ares",
        "round": 1,
        "content": "bull case",
        "timestamp": "2026-05-17T12:00:00Z",
    }
    base.update(kw)
    return base


# ─── Build bundle ─────────────────────────────────────────────────────


def test_build_bundle_rejects_empty_events():
    with pytest.raises(ValueError):
        build_bundle([], thesis_id="t", market_id="m")


def test_build_bundle_requires_trace_id():
    with pytest.raises(ValueError):
        # event with no trace_id + no override
        build_bundle(
            [{"event_id": "e", "event_type": "x"}],
            thesis_id="t",
            market_id="m",
        )


def test_build_bundle_infers_trace_id_from_first_event():
    b = build_bundle(
        [_ev(trace_id="inferred-trace")],
        thesis_id="t",
        market_id="m",
    )
    assert b.metadata.trace_id == "inferred-trace"


def test_build_bundle_counts_distinct_agents():
    events = [
        _ev(agent="ares"),
        _ev(agent="athena", event_type="vote"),
        _ev(agent="zeus", event_type="veto"),
        _ev(agent="ares"),  # duplicate — same agent
        _ev(agent=None, event_type="deliberation_start"),  # ignored
    ]
    b = build_bundle(events, thesis_id="t", market_id="m", trace_id="x")
    assert b.metadata.council_size == 3


def test_build_bundle_collects_rounds_sorted():
    events = [
        _ev(round=4),
        _ev(round=1),
        _ev(round=3),
        _ev(round=None, event_type="deliberation_start"),
    ]
    b = build_bundle(events, thesis_id="t", market_id="m", trace_id="x")
    assert b.metadata.rounds == (1, 3, 4)


def test_build_bundle_event_count_matches_input():
    events = [_ev() for _ in range(7)]
    b = build_bundle(events, thesis_id="t", market_id="m", trace_id="x")
    assert b.metadata.event_count == 7


# ─── Determinism + hash ───────────────────────────────────────────────


def test_bundle_hash_deterministic_for_identical_input():
    """Same events, same metadata → same hash."""
    events = [_ev() for _ in range(3)]
    a = build_bundle(events, thesis_id="t", market_id="m", trace_id="x")
    b = build_bundle(events, thesis_id="t", market_id="m", trace_id="x")
    assert a.bundle_hash == b.bundle_hash


def test_bundle_hash_changes_with_content():
    a = build_bundle([_ev(content="bull case")], thesis_id="t", market_id="m", trace_id="x")
    b = build_bundle([_ev(content="bear case")], thesis_id="t", market_id="m", trace_id="x")
    assert a.bundle_hash != b.bundle_hash


def test_bundle_hash_changes_with_event_order():
    """Order matters — re-ordering events is a different bundle."""
    e1 = _ev(content="first")
    e2 = _ev(content="second")
    a = build_bundle([e1, e2], thesis_id="t", market_id="m", trace_id="x")
    b = build_bundle([e2, e1], thesis_id="t", market_id="m", trace_id="x")
    assert a.bundle_hash != b.bundle_hash


def test_bundle_hash_starts_with_0x():
    b = build_bundle([_ev()], thesis_id="t", market_id="m", trace_id="x")
    assert b.bundle_hash.startswith("0x")
    assert len(b.bundle_hash) == 66  # 0x + 64 hex chars (keccak256)


def test_canonical_bytes_round_trip():
    b = build_bundle([_ev()], thesis_id="t", market_id="m", trace_id="x")
    # canonical_bytes is what gets pinned to IPFS — it must be valid
    # JSON we can decode back.
    import json as _json
    parsed = _json.loads(b.canonical_bytes.decode("utf-8"))
    assert "metadata" in parsed
    assert "events" in parsed
    assert parsed["events"][0]["agent"] == "ares"


# ─── Pydantic + dataclass event support ──────────────────────────────


@dataclass
class _PseudoEvent:
    """Stands in for a dataclass-shaped event source."""

    trace_id: str
    event_id: str
    thesis_id: str
    signal_id: str
    market_id: str
    event_type: str
    agent: str | None
    round: int | None
    content: str
    timestamp: str


def test_build_bundle_accepts_dataclass_events():
    ev = _PseudoEvent(
        trace_id="t", event_id="e", thesis_id="th", signal_id="s",
        market_id="m", event_type="agent_output", agent="ares", round=1,
        content="bull", timestamp="2026-05-17T12:00Z",
    )
    b = build_bundle([ev], thesis_id="th", market_id="m", trace_id="t")
    assert b.metadata.event_count == 1
    assert b.events[0]["agent"] == "ares"


def test_build_bundle_rejects_unknown_event_type():
    with pytest.raises(TypeError):
        build_bundle(["not a real event"], thesis_id="t", market_id="m", trace_id="x")


# ─── Anchor payload ───────────────────────────────────────────────────


def test_to_anchor_payload_minimal():
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    anchor = to_anchor_payload(b)
    assert anchor.thesis_id == "th"
    assert anchor.market_id == "m"
    assert anchor.bundle_hash == b.bundle_hash
    assert anchor.cid_v0 is None  # not pinned yet


def test_to_anchor_payload_with_cid():
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    anchor = to_anchor_payload(b, cid_v0="QmTest123")
    assert anchor.cid_v0 == "QmTest123"


def test_to_anchor_payload_uses_supplied_timestamp():
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    ts = datetime(2026, 5, 17, 14, 0, tzinfo=timezone.utc)
    anchor = to_anchor_payload(b, anchored_at=ts)
    assert anchor.anchored_at == ts.isoformat()


# ─── Verify ───────────────────────────────────────────────────────────


def test_verify_bundle_round_trip():
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    assert verify_bundle(b, b.bundle_hash) is True
    assert verify_bundle(b, "0x" + "deadbeef" * 8) is False


# ─── JSON dump ────────────────────────────────────────────────────────


def test_bundle_to_json_is_valid_json_string():
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    import json as _json
    parsed = _json.loads(bundle_to_json(b))
    assert parsed["metadata"]["thesis_id"] == "th"


def test_bundle_to_json_distinct_from_canonical_bytes():
    """Pretty JSON is not byte-stable; canonical_bytes is.

    Verify by checking lengths differ (formatting adds whitespace).
    """
    b = build_bundle([_ev()], thesis_id="th", market_id="m", trace_id="t")
    pretty = bundle_to_json(b)
    assert len(pretty.encode()) > len(b.canonical_bytes)
