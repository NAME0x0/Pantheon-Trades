# Parthenon — Archive

Permanent storage service for all Pantheon Trades artifacts.

## What It Does

1. Archives signals, theses, traces, trades, and outcomes to IPFS + Irys
2. Builds daily Merkle trees and anchors roots on Arc Testnet
3. Manages ERC-8004 agent passport operations
4. Prevents duplicate archive writes via content hash deduplication

## Setup

```bash
cd services/parthenon
cp .env.example .env
# Requires IPFS_API_URL, IRYS_KEY, ARC_RPC_URL
uv run python -m parthenon
```

## Structure

```
src/parthenon/
  archive.py          Main archive orchestration
  hash.py             Content hashing utilities
  ipfs.py             IPFS client
  irys.py             Irys bundler client
  local.py            Local/PostgreSQL fast storage
  anchor.py           On-chain Merkle root anchoring
  manifest.py         ArchiveManifest construction
  merkle.py           Merkle tree builder
  replay.py           Deduplication and replay protection
  passport.py         ERC-8004 passport high-level API
  erc8004_client.py   Raw ERC-8004 contract client
  identity.py         IdentityRegistry wrapper
  reputation.py       ReputationRegistry wrapper
  validation.py       ValidationRegistry wrapper
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/PARTHENON.md` — full service documentation
- `docs/ERC8004_INTEGRATION.md` — ERC-8004 details
- `docs/REPLAY_PROTECTION.md` — deduplication
- `docs/ARC_INTEGRATION.md` — Arc Testnet setup
