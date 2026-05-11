# Role-Based Access Control

## Roles

| Role | Description |
|------|-------------|
| `viewer` | Read-only access to signals, theses, traces, leaderboard |
| `operator` | Full read + manual overrides, strategy management |
| `admin` | operator + governance actions, ZeusMultisig operations |

## Permissions Matrix

| Action | viewer | operator | admin |
|--------|--------|----------|-------|
| View signals | ✓ | ✓ | ✓ |
| View theses | ✓ | ✓ | ✓ |
| View trades | ✓ | ✓ | ✓ |
| View traces | ✓ | ✓ | ✓ |
| View leaderboard | ✓ | ✓ | ✓ |
| View agent passports | ✓ | ✓ | ✓ |
| View Arc proofs | ✓ | ✓ | ✓ |
| Manual exit override | — | ✓ | ✓ |
| Pause new entries | — | ✓ | ✓ |
| Strategy management | — | ✓ | ✓ |
| Goals board write | — | ✓ | ✓ |
| Emergency pause | — | — | ✓ |
| ZeusMultisig proposals | — | — | ✓ |
| Risk policy changes | — | — | ✓ (+ ZMS) |
| Agent exile confirm | — | — | ✓ |
| Human review queue | — | ✓ | ✓ |

## Role Assignment

Roles assigned by existing admin. Stored in `user_roles` table in PostgreSQL.

```sql
CREATE TABLE user_roles (
    address TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP  -- NULL = never expires
);
```

## FastAPI Dependency

```python
# In route handler
@router.post("/manual-exit/{position_id}")
async def manual_exit(
    position_id: str,
    user: User = Depends(require_role("operator"))
):
    ...
```

`require_role(role)` raises 403 if `user.role` does not satisfy the required level.

Role hierarchy: `admin > operator > viewer`

## Default Access

New wallet addresses have no role by default — access denied to all non-public endpoints until explicitly granted a role.
