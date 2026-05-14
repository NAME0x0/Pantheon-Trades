"""Canonical role strings used across RBAC checks."""

from __future__ import annotations

from typing import Final

ROLE_VIEWER: Final[str] = "viewer"
ROLE_OPERATOR: Final[str] = "operator"
ROLE_ADMIN: Final[str] = "admin"

ALL_ROLES: Final[frozenset[str]] = frozenset({ROLE_VIEWER, ROLE_OPERATOR, ROLE_ADMIN})

# Roles ordered from least to most powerful for "minimum role" checks.
ROLE_ORDER: Final[tuple[str, ...]] = (ROLE_VIEWER, ROLE_OPERATOR, ROLE_ADMIN)


def role_rank(role: str) -> int:
    try:
        return ROLE_ORDER.index(role)
    except ValueError:
        return -1


def at_least(role: str, minimum: str) -> bool:
    return role_rank(role) >= role_rank(minimum)
