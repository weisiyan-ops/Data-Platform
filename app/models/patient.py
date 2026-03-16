"""Patient demographics model."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import Sex
from app.models.provenance import ProvenanceRecord


class Patient(BaseModel):
    """Core patient demographics record."""

    patient_id: str
    project_id: str
    mrn: str | None = None
    sex: Sex | None = None
    date_of_birth: date | None = None
    age_at_dx: int | None = None
    race: str | None = None
    ethnicity: str | None = None
    diagnosis_date: date | None = None
    death_date: date | None = None
    last_contact_date: date | None = None
    kps: int | None = None
    ecog: int | None = None
    smoking_status: str | None = None
    pack_years: float | None = None

    provenance: list[ProvenanceRecord] = []
