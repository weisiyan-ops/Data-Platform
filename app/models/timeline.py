"""Derived endpoint models — PFS, OS, local control."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.provenance import ProvenanceRecord


class DerivedEndpoints(BaseModel):
    """Computed endpoints for a patient — derived from timeline, not extracted."""

    endpoint_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None

    # Index date
    index_date: date | None = None
    index_date_definition: str | None = None  # e.g. "start_of_treatment"

    # Overall survival
    os_months: float | None = None
    os_event: bool | None = None  # True=death, False=censored
    os_censor_date: date | None = None
    os_censor_reason: str | None = None

    # Progression-free survival
    pfs_months: float | None = None
    pfs_event: bool | None = None  # True=progression/death, False=censored
    pfs_event_type: str | None = None  # "progression", "death"
    pfs_event_date: date | None = None
    pfs_censor_date: date | None = None

    # Local control
    lc_months: float | None = None
    lc_event: bool | None = None  # True=local failure
    lc_event_date: date | None = None

    provenance: list[ProvenanceRecord] = []
