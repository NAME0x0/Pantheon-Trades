"""RBAC helpers — declarative role gates for routers."""

from __future__ import annotations

from fastapi import HTTPException, status

from pantheon_api.auth.roles import ROLE_ADMIN, ROLE_OPERATOR, at_least
from pantheon_api.auth.session import SessionPayload


def require_min_role(payload: SessionPayload, minimum: str) -> None:
    if not any(at_least(role, minimum) for role in payload.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"requires role >= {minimum}",
        )


def require_admin(payload: SessionPayload) -> None:
    require_min_role(payload, ROLE_ADMIN)


def require_operator(payload: SessionPayload) -> None:
    require_min_role(payload, ROLE_OPERATOR)
