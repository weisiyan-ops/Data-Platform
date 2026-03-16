"""Patient CRUD stubs."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/")
def list_patients() -> dict:
    return {"message": "Not yet implemented — see Phase 2"}


@router.get("/{patient_id}")
def get_patient(patient_id: str) -> dict:
    return {"message": "Not yet implemented — see Phase 2", "patient_id": patient_id}
