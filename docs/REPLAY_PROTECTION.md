# Replay Protection

Multiple layers of replay protection prevent duplicate transactions, duplicate archives, and duplicate orders.

## Layer 1: SIWE Nonce (Authentication)

SIWE nonces are single-use, stored in Redis with 5-minute TTL. A replayed SIWE message (same nonce) returns 401 immediately.

## Layer 2: Archive Deduplication (Parthenon)

Every archive write is preceded by a content hash check:

```python
content_hash = keccak256(artifact.model_dump_json().encode())
if await db.hash_exists(content_hash):
    raise DuplicateArchiveError(content_hash)
```

A bloom filter provides O(1) probabilistic first check; PostgreSQL provides authoritative check.

Prevents the same signal, thesis, or trace from being archived twice (e.g., on service restart).

## Layer 3: Order Deduplication (Strategos)

Each order is tagged with a `client_order_id` derived from the `ApprovalToken`:

```python
client_order_id = f"{token.thesis_id[:8]}_{int(time.time())}"
```

Polymarket CLOB deduplicates on `client_order_id`. A duplicate submission returns the existing order, not a new fill.

Additionally, Strategos tracks pending orders in Redis. Before submitting, checks if a pending order for the same `thesis_id` already exists.

## Layer 4: On-Chain Replay Protection (Parthenon)

Before calling any Arc Testnet contract, Parthenon checks:

```python
# Check if already recorded on-chain
existing = await arc.call(contract, "getByHash", [content_hash])
if existing != bytes(32):  # non-zero = already exists
    return  # skip; already recorded
```

This prevents gas waste from duplicate on-chain calls and ensures contract state integrity.

## Layer 5: ApprovalToken Expiry

`ApprovalToken`s expire after 15 minutes. Strategos validates expiry before any order submission. Expired tokens cannot be replayed.

## Layer 6: Signal TTL

Signals expire after 15 minutes. A signal cannot trigger a second deliberation after TTL, even if it is somehow replayed into the queue.

## Audit

All duplicate attempts are logged at WARN level:
- `[DUPLICATE_ARCHIVE] hash={content_hash} artifact_type={type}`
- `[DUPLICATE_ORDER] thesis_id={id} client_order_id={id}`
- `[EXPIRED_TOKEN] token_id={id} expired_at={ts}`

Prometheus counter: `replay_protection_blocked_total` by layer.
