from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_counterfactual() -> dict:
    return {"items": [], "service": "counterfactual"}
