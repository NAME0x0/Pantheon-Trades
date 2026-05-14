from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_passports() -> dict:
    return {"items": [], "service": "passports"}
