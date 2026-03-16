"""Pipeline trigger stubs."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/extract")
def trigger_extraction() -> dict:
    return {"message": "Not yet implemented — see Phase 4"}


@router.post("/derive-endpoints")
def trigger_derive_endpoints() -> dict:
    return {"message": "Not yet implemented — see Phase 6"}
