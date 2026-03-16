"""Project CRUD stubs."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/")
def list_projects() -> dict:
    return {"message": "Not yet implemented — see Phase 2"}


@router.post("/")
def create_project() -> dict:
    return {"message": "Not yet implemented — see Phase 2"}


@router.get("/{project_id}")
def get_project(project_id: str) -> dict:
    return {"message": "Not yet implemented — see Phase 2", "project_id": project_id}
