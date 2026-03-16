"""Imaging report and RECIST assessment models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import RECISTCategory
from app.models.provenance import ProvenanceRecord


class LesionMeasurement(BaseModel):
    """A single lesion measurement within an imaging assessment."""

    lesion_id: str | None = None
    lesion_label: str | None = None  # e.g. "target_1", "non_target_liver"
    is_target: bool | None = None
    location: str | None = None
    longest_diameter_mm: float | None = None
    short_axis_mm: float | None = None  # for lymph nodes
    prior_diameter_mm: float | None = None
    status: str | None = None  # "present", "resolved", "new", "unchanged"


class ImagingReport(BaseModel):
    """An imaging study with optional RECIST assessment."""

    imaging_id: str
    patient_id: str
    project_id: str
    encounter_id: str | None = None
    study_date: date | None = None
    modality: str | None = None  # "CT", "MRI", "PET-CT", "X-ray"
    body_region: str | None = None
    indication: str | None = None
    findings_text: str | None = None
    impression_text: str | None = None

    # RECIST
    recist_category: RECISTCategory | None = None
    recist_timepoint: str | None = None  # "baseline", "week_6", etc.
    sum_longest_diameters_mm: float | None = None
    prior_sum_mm: float | None = None
    percent_change: float | None = None
    new_lesions: bool | None = None
    lesions: list[LesionMeasurement] = []

    provenance: list[ProvenanceRecord] = []
