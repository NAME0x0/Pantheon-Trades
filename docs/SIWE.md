# Sign-In With Ethereum (SIWE)

SIWE (EIP-4361) enables wallet-based authentication without passwords. Users sign a human-readable message with their Ethereum wallet.

## Why SIWE?

Pantheon Trades is an on-chain system — users hold portfolios tied to Ethereum addresses. SIWE aligns auth with on-chain identity, enabling:
- Agent passport verification (user controls the operator address on their passport)
- ZeusMultisig signing with the same wallet used for governance
- No separate password system to breach

## Implementation

### Nonce Endpoint
```
GET /api/auth/nonce
Response: { "nonce": "8f2a3b4c5d", "expires_at": "2024-01-01T00:05:00Z" }
```

Nonce stored in Redis with 5-minute TTL. Single-use: consumed on verify.

### Verify Endpoint
```
POST /api/auth/verify
Body: {
  "message": "<full SIWE message string>",
  "signature": "0x..."
}
Response: {
  "token": "eyJ...",
  "refresh_token": "...",
  "expires_at": "2024-01-02T00:00:00Z"
}
```

### Verification Logic
1. Parse SIWE message using `siwe` library
2. Verify nonce matches stored Redis nonce
3. Verify nonce not expired
4. Recover signer address from signature
5. Verify recovered address == `message.address`
6. Verify `message.domain` == API domain
7. Verify `message.chainId` == 5042002 (Arc Testnet)
8. Delete nonce from Redis (one-time use)
9. Issue JWT with address + role

### Refresh
```
POST /api/auth/refresh
Body: { "refresh_token": "..." }
Response: { "token": "...", "expires_at": "..." }
```

Refresh tokens are rotated on each use. Stored as hashed values in PostgreSQL.

## Client Integration

Web UI (`apps/web/lib/ws.ts`) uses wagmi/viem for wallet connection and SIWE signing:

```typescript
// Sign SIWE message
const message = createSiweMessage({
  domain: window.location.host,
  address,
  statement: "Welcome to Pantheon Trades. Sign to authenticate.",
  uri: window.location.origin,
  version: "1",
  chainId: 5042002,
  nonce: await fetchNonce(),
});

const signature = await walletClient.signMessage({ message });
const { token } = await verify(message, signature);
```

## Security Notes

- Nonces are random 10-character hex strings (sufficient entropy for 5-minute window)
- Replaying a used nonce returns 401 immediately
- Cross-chain replay prevented by Chain ID in message
- JWT signing key rotated monthly; stored in `JWT_SECRET` env var
