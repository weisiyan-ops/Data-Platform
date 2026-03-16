"""Progression and response event models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import ProgressionType, RECISTCategory
from app.models.provenance import ProvenanceRecord


class ProgressionEvent(BaseModel):
    """A disease progression event."""

    progression_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None
    event_date: date | None = None
    progression_type: ProgressionType | None = None
    site: str | None = None
    detection_method: str | None = None  # "imaging", "clinical", "pathologic"
    imaging_id: str | None = None  # link to ImagingReport
    notes: str | None = None

    provenance: list[ProvenanceRecord] = []


class ResponseEvent(BaseModel):
    """A treatment response assessment."""

    response_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None
    assessment_date: date | None = None
    best_response: RECISTCategory | None = None
    assessment_method: str | None = None
    imaging_id: str | None = None
    treatment_line: int | None = None
    notes: str | None = None

    provenance: list[ProvenanceRecord] = []
