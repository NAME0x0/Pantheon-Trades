"""Trace replay — reconstruct council vote/PnL math from an archived thesis."""

from __future__ import annotations

from pantheon_core.schema import Thesis


def summarise_thesis(thesis: Thesis) -> dict:
    return {
        "thesis_id": thesis.thesis_id,
        "market_id": thesis.market_id,
        "direction": thesis.direction,
        "council_probability": thesis.council_probability,
        "raw_market_probability": thesis.raw_market_probability,
        "edge": thesis.edge,
        "confidence": thesis.confidence,
        "recommended_size_pct": thesis.recommended_size_pct,
        "kelly_fraction": thesis.kelly_fraction,
        "vote_summary": thesis.vote_summary,
        "weighted_approval": thesis.weighted_approval,
        "zeus_veto": thesis.zeus_veto,
        "solon_veto": thesis.solon_veto,
        "cassandra_flags": thesis.cassandra_flags,
        "humans_flags": thesis.humans_flags,
        "hephaestus_flags": thesis.hephaestus_flags,
        "agents": [v.model_dump() for v in thesis.agents],
        "duration_ms": thesis.deliberation_duration_ms,
        "status": thesis.status,
    }
