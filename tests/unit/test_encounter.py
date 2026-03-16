"""Tests for Encounter model."""

from datetime import date

from app.models.encounter import Encounter
from app.models.enums import EncounterType


def test_encounter_round_trip():
    enc = Encounter(
        encounter_id="E001",
        patient_id="P1",
        project_id="proj1",
        encounter_type=EncounterType.OUTPATIENT,
        encounter_date=date(2024, 6, 1),
        department="Radiation Oncology",
    )
    data = enc.model_dump()
    restored = Encounter.model_validate(data)
    assert restored.encounter_type == EncounterType.OUTPATIENT
    assert restored.department == "Radiation Oncology"


def test_encounter_minimal():
    enc = Encounter(encounter_id="E002", patient_id="P1", project_id="proj1")
    assert enc.encounter_type is None
    assert enc.provenance == []
