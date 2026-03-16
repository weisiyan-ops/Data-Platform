"""Encounter / visit context model."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import EncounterType
from app.models.provenance import ProvenanceRecord


class Encounter(BaseModel):
    """A clinical encounter or visit."""

    encounter_id: str
    patient_id: str
    project_id: str
    encounter_type: EncounterType | None = None
    encounter_date: date | None = None
    admit_datetime: datetime | None = None
    discharge_datetime: datetime | None = None
    department: str | None = None
    facility: str | None = None
    provider_name: str | None = None
    provider_specialty: str | None = None
    chief_complaint: str | None = None

    provenance: list[ProvenanceRecord] = []
