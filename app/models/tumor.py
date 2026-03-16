"""Tumor assessment / staging model."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import ClinicalStageGroup, Grade, StagingSystem
from app.models.provenance import ProvenanceRecord


class TumorAssessmentEvent(BaseModel):
    """A staging or tumor assessment event."""

    assessment_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None
    assessment_date: date | None = None

    # TNM
    clinical_t: str | None = None
    clinical_n: str | None = None
    clinical_m: str | None = None
    pathologic_t: str | None = None
    pathologic_n: str | None = None
    pathologic_m: str | None = None

    # Overall stage
    stage_group: ClinicalStageGroup | None = None
    staging_system: StagingSystem | None = None
    staging_edition: str | None = None

    # Histology / grade
    grade: Grade | None = None
    tumor_size_cm: float | None = None
    lymph_nodes_examined: int | None = None
    lymph_nodes_positive: int | None = None

    # Biomarkers (common across cancers)
    biomarkers: dict[str, str | float | bool | None] | None = None

    provenance: list[ProvenanceRecord] = []
