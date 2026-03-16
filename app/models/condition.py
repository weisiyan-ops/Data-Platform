"""Diagnosis / cancer condition model."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import CancerType, HistologyGroup
from app.models.provenance import ProvenanceRecord


class Condition(BaseModel):
    """A cancer diagnosis or condition."""

    condition_id: str
    patient_id: str
    project_id: str
    cancer_type: CancerType | None = None
    icd10_code: str | None = None
    icd10_description: str | None = None
    histology: HistologyGroup | None = None
    histology_text: str | None = None
    primary_site: str | None = None
    laterality: str | None = None
    diagnosis_date: date | None = None
    is_primary: bool | None = None
    is_recurrence: bool | None = None

    provenance: list[ProvenanceRecord] = []
