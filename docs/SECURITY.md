# Security

## Overview

Pantheon Trades handles real capital and on-chain transactions. Security is a first-class concern at every layer.

## Threat Model

See `docs/THREAT_MODEL.md` for full threat analysis.

## Authentication

- SIWE (Sign-In With Ethereum) — no passwords, no password breach surface
- JWT with short expiry (24h access, 30d refresh)
- Nonces are single-use, Redis-backed, 5-minute TTL
- Chain ID in SIWE message prevents cross-chain replay

See `docs/AUTH.md` and `docs/SIWE.md`.

## Authorization

- RBAC with three roles: viewer / operator / admin
- FastAPI dependency guards on every protected route
- ZeusMultisig required for governance actions (risk policy, agent exiles)

See `docs/RBAC.md`.

## API Security

- CORS restricted to known frontend origins
- Rate limiting: 60 req/min unauthenticated, 300 req/min authenticated
- Webhook signatures verified via HMAC-SHA256
- Input validation via Pydantic on all request bodies
- SQL queries via parameterized ORM only (no raw string interpolation)

## Smart Contract Security

- `PantheonConstitution.sol` is non-upgradeable
- All upgradeable contracts protected by ZeusMultisig (72h timelock, 3/5 signers)
- `EmergencyPause.sol` allows instant halt without timelock
- Reentrancy guards on all fund-handling functions
- Access control via `RoleManager.sol` and `Roles.sol` library

See `docs/ZEUS_MULTISIG.md` and `docs/EMERGENCY_PAUSE.md`.

## Key Management

- Private keys: never in code or logs
- `PRIVATE_KEY` env var — operator hot wallet (low funds; only for gas + on-chain ops)
- ZeusMultisig keys: held by 5 separate operators
- API keys: stored in env vars, rotated quarterly

## Secrets in Code

Pre-commit hook (`secrets-guardian` skill) scans for:
- Private key patterns
- API key patterns
- `.env` files accidentally staged

## Replay Protection

- SIWE nonces: single-use
- Archive writes: deduplication by content hash (see Parthenon)
- On-chain: `replay.py` tracks submitted transactions; no duplicate submissions
- Trade IDs: uuid4, never reused

See `docs/REPLAY_PROTECTION.md`.

## Logging and Auditing

- All API requests logged with user address, timestamp, endpoint, response code
- All on-chain transactions logged with tx hash
- No sensitive data (private keys, API keys) in logs
- Logs shipped to centralized store; retained 90 days
- Traces permanently archived in IPFS

## Dependency Security

- Monthly `uv audit` runs for Python packages
- Monthly `pnpm audit` for JS packages
- Foundry dependencies pinned to specific commits
- Pre-release check via `docs/FOUNDRY_SETUP.md`

## Incident Response

See `docs/EMERGENCY_PAUSE.md` for the pause playbook.

On breach:
1. Trigger EmergencyPause via ZeusMultisig
2. Notify all admin holders
3. Rotate affected credentials
4. Post-mortem via Underworld
5. Fix + audit before resume
