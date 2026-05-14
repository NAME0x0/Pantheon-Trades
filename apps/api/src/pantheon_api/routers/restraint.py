from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_restraint() -> dict:
    return {"items": [], "service": "restraint"}
