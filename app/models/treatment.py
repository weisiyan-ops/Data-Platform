"""Treatment models — medications and procedures."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.enums import TreatmentIntent, TreatmentModality
from app.models.provenance import ProvenanceRecord


class MedicationExposure(BaseModel):
    """A medication administration or prescription period."""

    medication_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None
    encounter_id: str | None = None
    drug_name: str | None = None
    generic_name: str | None = None
    drug_class: str | None = None
    modality: TreatmentModality | None = None
    intent: TreatmentIntent | None = None
    regimen_name: str | None = None
    cycle_number: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    dose: str | None = None
    dose_unit: str | None = None
    route: str | None = None
    frequency: str | None = None
    reason_stopped: str | None = None

    provenance: list[ProvenanceRecord] = []


class ProcedureEvent(BaseModel):
    """A surgical or procedural event."""

    procedure_id: str
    patient_id: str
    project_id: str
    condition_id: str | None = None
    encounter_id: str | None = None
    procedure_name: str | None = None
    procedure_code: str | None = None
    code_system: str | None = None
    modality: TreatmentModality | None = None
    intent: TreatmentIntent | None = None
    procedure_date: date | None = None
    surgeon: str | None = None
    findings: str | None = None
    margin_status: str | None = None

    # Radiation-specific
    total_dose_gy: float | None = None
    fractions: int | None = None
    technique: str | None = None
    treatment_site: str | None = None

    provenance: list[ProvenanceRecord] = []
