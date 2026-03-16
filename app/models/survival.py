"""Survival event models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import VitalStatus
from app.models.provenance import ProvenanceRecord


class SurvivalEvent(BaseModel):
    """A death or last-follow-up event."""

    survival_id: str
    patient_id: str
    project_id: str
    vital_status: VitalStatus | None = None
    death_date: date | None = None
    cause_of_death: str | None = None
    cancer_related_death: bool | None = None
    last_contact_date: date | None = None
    last_known_alive_date: date | None = None

    provenance: list[ProvenanceRecord] = []
