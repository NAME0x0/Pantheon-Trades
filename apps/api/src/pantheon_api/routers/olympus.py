from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_olympus() -> dict:
    return {"items": [], "service": "olympus"}
