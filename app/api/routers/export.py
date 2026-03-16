"""Export stubs."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/csv")
def export_csv() -> dict:
    return {"message": "Not yet implemented — see Phase 8"}
