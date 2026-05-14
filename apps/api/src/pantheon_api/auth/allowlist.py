"""Address allowlist — operator/admin wallets are explicit."""

from __future__ import annotations

import os

from pantheon_api.auth.roles import ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER


def _parse(env_value: str | None) -> set[str]:
    if not env_value:
        return set()
    return {a.strip().lower() for a in env_value.split(",") if a.strip()}


def roles_for(address: str) -> list[str]:
    """Return the set of roles assigned to a wallet address.

    Anyone with a valid SIWE login gets ``viewer``. Operators and admins
    are configured via ``PANTHEON_OPERATORS`` and ``PANTHEON_ADMINS`` env
    vars (comma-separated 0x-addresses).
    """
    addr = address.lower()
    admins = _parse(os.environ.get("PANTHEON_ADMINS"))
    operators = _parse(os.environ.get("PANTHEON_OPERATORS"))
    roles = [ROLE_VIEWER]
    if addr in operators or addr in admins:
        roles.append(ROLE_OPERATOR)
    if addr in admins:
        roles.append(ROLE_ADMIN)
    return roles
