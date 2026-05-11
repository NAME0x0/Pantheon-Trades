# Parthenon — Archive

The Parthenon (Παρθενών), temple of Athena, was the most enduring structure in Athens — permanent, sacred, and authoritative. In Pantheon Trades, Parthenon is the archival service responsible for permanent storage of all system artifacts.

## Responsibilities

1. Archive signals, theses, traces, and outcomes to IPFS
2. Ensure permanent storage via Irys bundler
3. Build daily Merkle trees over archived content
4. Anchor Merkle roots on-chain (Arc Testnet)
5. Manage ERC-8004 agent passport read/write
6. Prevent replay attacks on archive writes

## Storage Tiers

| Tier | Store | Durability | Access |
|------|-------|-----------|--------|
| Fast | PostgreSQL | Local | Milliseconds |
| Mutable archive | IPFS | Until unpinned | Seconds |
| Permanent | Irys | Permanent (endowment) | Seconds |
| On-chain | Arc Testnet | Blockchain durability | On-chain query |

Every artifact is written to all tiers. The on-chain anchor is the source of truth for integrity.

## Archive Pipeline

```python
async def archive(artifact: Archivable) -> ArchiveManifest:
    # 1. Serialize and hash
    content_bytes = artifact.model_dump_json().encode()
    content_hash = keccak256(content_bytes)
    
    # Replay protection: reject if already archived
    if await db.hash_exists(content_hash):
        raise DuplicateArchiveError(content_hash)
    
    # 2. Pin to IPFS
    cid = await ipfs.add(content_bytes)
    
    # 3. Upload to Irys
    irys_receipt = await irys.upload(content_bytes, tags=artifact.irys_tags())
    
    # 4. Record locally
    await db.record_archive(content_hash, cid, irys_receipt.id)
    
    # 5. Add to daily Merkle tree
    await merkle.add_leaf(content_hash)
    
    return ArchiveManifest(cid=cid, irys_id=irys_receipt.id, hash=content_hash)
```

## Merkle Tree

Each day, all archived content hashes are leaves in a Merkle tree.

At 00:00 UTC, the day's Merkle root is computed and anchored on-chain:

```python
await anchor.anchor_root(
    root=merkle.compute_root(),
    date=today,
    leaf_count=merkle.leaf_count
)
```

`anchor.py` calls `Parthenon.sol` on Arc Testnet with the root hash.

This means any artifact from any day can be proven as "included in the archive" by providing a Merkle proof against the on-chain root.

## Replay Protection

`replay.py` maintains a bloom filter + database of all archived content hashes. Any attempt to archive the same content twice is rejected before IPFS upload.

## ERC-8004 Client

`erc8004_client.py` wraps all calls to Arc Testnet ERC-8004 contracts:
- `IdentityRegistry` — agent passport CRUD
- `ReputationRegistry` — reputation event logging
- `ValidationRegistry` — audit record writing

Uses the Canteen Arc RPC. Auth: `ARC_RPC_URL` env var with embedded key.

## Agent Identity Operations

`identity.py`, `reputation.py`, `validation.py` — domain-specific wrappers for ERC-8004 operations.

`passport.py` — high-level API used by other services to create/read/update agent passports.

## Manifest Schema

```python
class ArchiveManifest(BaseModel):
    artifact_type: str      # "signal" | "thesis" | "trace" | "trade" | "outcome"
    artifact_id: str
    content_hash: str       # keccak256 hex
    ipfs_cid: str
    irys_id: str
    anchored: bool
    merkle_root: str | None
    archived_at: datetime
```

## Service Files

`services/parthenon/`:
- `hash.py` — content hashing utilities
- `ipfs.py` — IPFS client
- `irys.py` — Irys bundler client
- `local.py` — PostgreSQL fast-path storage
- `anchor.py` — on-chain Merkle root anchoring
- `manifest.py` — ArchiveManifest construction
- `merkle.py` — Merkle tree builder
- `replay.py` — deduplication and replay protection
- `passport.py` — ERC-8004 passport high-level API
- `erc8004_client.py` — raw ERC-8004 contract client
- `identity.py`, `reputation.py`, `validation.py` — registry wrappers
- `archive.py` — main archive orchestration
