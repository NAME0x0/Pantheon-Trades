# Authentication

## Overview

Pantheon Trades uses Sign-In With Ethereum (SIWE) for authentication, issuing JWTs for session management.

## Flow

```
1. Client requests challenge nonce
   GET /api/auth/nonce → { nonce: "abc123", expires_at: "..." }

2. Client signs SIWE message with wallet
   Message includes: domain, address, statement, nonce, issued-at

3. Client submits signed message
   POST /api/auth/verify → { token: "JWT...", expires_at: "..." }

4. Client uses JWT for all subsequent requests
   Authorization: Bearer <JWT>
```

## JWT Claims

```json
{
  "sub": "0xWalletAddress",
  "role": "operator",
  "iat": 1704067200,
  "exp": 1704153600,
  "iss": "pantheon-trades"
}
```

JWT expiry: 24 hours. Refresh tokens: 30 days.

## SIWE Message

```
pantheon-trades.app wants you to sign in with your Ethereum account:
0xYourAddress

Welcome to Pantheon Trades. Sign to authenticate.

URI: https://pantheon-trades.app
Version: 1
Chain ID: 5042002
Nonce: abc123
Issued At: 2024-01-01T00:00:00Z
```

Chain ID matches Arc Testnet (5042002) to prevent replay across chains.

## Roles

See `docs/RBAC.md` for role definitions and permissions.

Roles are assigned by admin and stored in PostgreSQL. An address's role is embedded in the JWT at sign-in.

## Nonce

Nonces are single-use, stored in Redis with 5-minute TTL. Prevents replay attacks at the SIWE layer.

## Dependencies

`apps/api/src/pantheon_api/deps.py` exports:
- `get_current_user(token: JWT) → User` — JWT validator
- `require_role(role: str) → Dependency` — role guard for route handlers
