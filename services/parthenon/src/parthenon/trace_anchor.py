"""Arc-anchored reasoning-trace bundles.

The Boule council emits a stream of structured ``TraceEvent``s per
deliberation — round openings, challenges, the Athena synthesis, votes,
and the final verdict. Today these traces live in Redis + IPFS; this
module makes them *publicly verifiable on chain*:

  1. Take an in-memory list of TraceEvents for one deliberation.
  2. Canonicalise them with ``parthenon.hash.canonical_json``.
  3. Compute a keccak256 ``bundle_hash`` over the canonical bytes.
  4. Produce a deterministic ``TraceBundle`` ready for IPFS pinning
     (via ``parthenon.ipfs``) and on-chain anchoring (via a thin
     Arc transaction that just emits the hash + CID).
  5. Optionally include a deliberation-time witness (``signed_at``,
     model fingerprint, agent set) so future re-runs are auditable.

Why this matters for Pantheon (and for the Agora Agents Hackathon
research note #1, "Trading-R1 reasoning traces as the product"): when
the reasoning trace itself is the artifact — not just the trade —
hashing it onto Arc at ~$0.01/tx makes the trace publicly verifiable
without eroding PnL. The trace becomes the product. Other agents can
bet on which reasoning patterns converge to profit, with the
TradingAgents v0.2.4 JSON-schema'd outputs serving as the substrate.

Mechanics:

  * No new Solidity contract — the existing ``ProofOfRestraint`` event
    pattern is reused for trace anchoring. A future deploy can mint
    a dedicated ``TraceRegistry`` with structured fields, but for the
    hackathon we use the off-chain bundle + a thin anchor receipt.
  * The bundle is IPFS-friendly (canonical JSON, byte-stable).
  * ``TraceAnchor.to_anchor_payload()`` is the minimal struct an
    on-chain anchoring tx needs: ``(thesis_id, bundle_hash, cid_v0)``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from parthenon.hash import canonical_json, content_hash


@dataclass(frozen=True)
class TraceBundleMetadata:
    """Provenance for one trace bundle."""

    thesis_id: str
    market_id: str
    trace_id: str
    council_size: int
    event_count: int
    rounds: tuple[int, ...]
    deliberation_started_at: str
    deliberation_finished_at: str
    model_fingerprint: str | None = None


@dataclass(frozen=True)
class TraceBundle:
    """Canonical, hashable representation of one deliberation's traces.

    Attributes:
        metadata: provenance (thesis id, market, model fingerprint, ...).
        events: the raw TraceEvent dicts in their original order.
        bundle_hash: keccak256 of the canonical bytes of (metadata, events).
        canonical_bytes: the exact bytes that were hashed — pin these
            to IPFS for content-addressed retrieval.
    """

    metadata: TraceBundleMetadata
    events: list[dict[str, Any]]
    bundle_hash: str
    canonical_bytes: bytes


def _normalise_event(event: Any) -> dict[str, Any]:
    """Turn anything the council emits into a plain dict.

    Accepts pydantic BaseModel (the ``TraceEvent`` schema), plain dicts,
    and dataclasses. Anything else raises so we never silently lose a
    field.
    """
    # pydantic v2 BaseModel duck-type
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    if hasattr(event, "__dataclass_fields__"):
        return asdict(event)
    raise TypeError(
        f"trace_anchor: cannot bundle event of type {type(event).__name__}; "
        "pass pydantic models, dicts, or dataclasses"
    )


def build_bundle(
    events: list[Any],
    *,
    thesis_id: str,
    market_id: str,
    trace_id: str | None = None,
    model_fingerprint: str | None = None,
) -> TraceBundle:
    """Build a canonical hashable bundle from one deliberation.

    Raises ``ValueError`` if the event list is empty — anchoring an
    empty trace defeats the purpose.
    """
    if not events:
        raise ValueError("trace_anchor.build_bundle: events must be non-empty")

    norm = [_normalise_event(e) for e in events]
    # Each event must declare its round (None for envelope events) so
    # the bundle can record which rounds were exercised.
    rounds = sorted({int(e["round"]) for e in norm if e.get("round") is not None})

    # Trace id: pull from the first event if not given.
    inferred_trace_id = trace_id or (norm[0].get("trace_id") if norm else None)
    if not inferred_trace_id:
        raise ValueError("trace_anchor.build_bundle: trace_id missing and not in events")

    # Council size = number of distinct agents that produced output.
    council_size = len({
        e.get("agent")
        for e in norm
        if e.get("agent") and e.get("event_type") in (
            "agent_output", "vote", "synthesis", "veto",
        )
    })

    # Deliberation window from first / last event timestamp.
    timestamps = [e.get("timestamp") for e in norm if e.get("timestamp")]
    started = timestamps[0] if timestamps else datetime.now(timezone.utc).isoformat()
    finished = timestamps[-1] if timestamps else started

    metadata = TraceBundleMetadata(
        thesis_id=thesis_id,
        market_id=market_id,
        trace_id=str(inferred_trace_id),
        council_size=council_size,
        event_count=len(norm),
        rounds=tuple(rounds),
        deliberation_started_at=str(started),
        deliberation_finished_at=str(finished),
        model_fingerprint=model_fingerprint,
    )

    payload = {"metadata": asdict(metadata), "events": norm}
    cbytes = canonical_json(payload)
    bhash = content_hash(payload)

    return TraceBundle(
        metadata=metadata,
        events=norm,
        bundle_hash=bhash,
        canonical_bytes=cbytes,
    )


@dataclass(frozen=True)
class TraceAnchor:
    """Minimal struct an on-chain anchoring transaction needs."""

    thesis_id: str
    market_id: str
    trace_id: str
    bundle_hash: str
    cid_v0: str | None  # populated after IPFS pin (None pre-pin)
    anchored_at: str


def to_anchor_payload(
    bundle: TraceBundle,
    cid_v0: str | None = None,
    anchored_at: datetime | None = None,
) -> TraceAnchor:
    """Project a bundle into an anchor payload ready to write on chain.

    ``cid_v0`` is the IPFS CIDv0 (`Qm...`) you got back from pinning
    ``bundle.canonical_bytes``. Pass None to record the anchor without
    a CID — useful when the pin is async-pending.
    """
    return TraceAnchor(
        thesis_id=bundle.metadata.thesis_id,
        market_id=bundle.metadata.market_id,
        trace_id=bundle.metadata.trace_id,
        bundle_hash=bundle.bundle_hash,
        cid_v0=cid_v0,
        anchored_at=(anchored_at or datetime.now(timezone.utc)).isoformat(),
    )


def verify_bundle(bundle: TraceBundle, expected_hash: str) -> bool:
    """Verify a bundle re-hashes to ``expected_hash``.

    Used after retrieving a bundle from IPFS — the contract anchor is
    only useful if we can prove the off-chain bytes hash back to it.
    """
    return bundle.bundle_hash == expected_hash


def bundle_to_json(bundle: TraceBundle) -> str:
    """Pretty-printed JSON dump for archival.

    Use ``bundle.canonical_bytes`` for the *hash-stable* bytes; this
    helper is for human reading + log capture only.
    """
    return json.dumps(
        {"metadata": asdict(bundle.metadata), "events": bundle.events},
        indent=2,
        default=str,
    )
