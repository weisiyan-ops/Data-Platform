"""Project-level metadata model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import CancerType


class ProjectMeta(BaseModel):
    """Study-level container for a research project."""

    project_id: str
    project_name: str
    cancer_type: CancerType | None = None
    description: str | None = None
    pi_name: str | None = None
    institution: str | None = None
    irb_number: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    config_path: str | None = None
    data_dir: str | None = None
    output_dir: str | None = None
    patient_count: int | None = None
