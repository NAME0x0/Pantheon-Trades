"""ProofOfRestraint router — reasons we declined to trade.

Each entry pulls the Redis stream record (canonical) and merges in any
on-chain anchor metadata written by the Areopagus chain writer
(``areopagus:restraint:tx:<proof_id>``) so callers see the Arcscan link
when the witness has landed.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_restraint(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    raw_entries = await redis.xrevrange("areopagus:restraint", count=limit)
    items: list[dict] = []
    proof_ids: list[str] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if not payload:
            continue
        try:
            entry = json.loads(payload)
        except (ValueError, json.JSONDecodeError):
            continue
        items.append(entry)
        if pid := entry.get("proof_id"):
            proof_ids.append(str(pid))

    if proof_ids:
        keys = [f"areopagus:restraint:tx:{pid}" for pid in proof_ids]
        tx_blobs = await redis.mget(keys)
        for entry, blob in zip(items, tx_blobs):
            if not blob:
                continue
            try:
                tx = json.loads(blob)
            except (ValueError, json.JSONDecodeError):
                continue
            entry["tx_hash"] = tx.get("tx_hash")
            entry["onchain_proof_id"] = tx.get("onchain_proof_id")
            entry["explorer_url"] = tx.get("explorer_url")

    return {"items": items, "count": len(items)}
