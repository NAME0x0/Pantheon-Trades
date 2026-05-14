from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_adversarial() -> dict:
    return {"items": [], "service": "adversarial"}
