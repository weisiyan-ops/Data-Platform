"""Lab result model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.provenance import ProvenanceRecord


class LabResult(BaseModel):
    """A laboratory test result."""

    lab_id: str
    patient_id: str
    project_id: str
    encounter_id: str | None = None
    analyte_name: str | None = None
    analyte_code: str | None = None  # LOINC code
    code_system: str | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    abnormal_flag: str | None = None  # "H", "L", "HH", "LL", "N"
    collection_datetime: datetime | None = None
    result_datetime: datetime | None = None

    provenance: list[ProvenanceRecord] = []
