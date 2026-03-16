"""Tests for treatment models."""

from datetime import date

from app.models.enums import TreatmentIntent, TreatmentModality
from app.models.treatment import MedicationExposure, ProcedureEvent


def test_medication_round_trip():
    med = MedicationExposure(
        medication_id="MED001",
        patient_id="P1",
        project_id="proj1",
        drug_name="Osimertinib",
        modality=TreatmentModality.TARGETED_THERAPY,
        intent=TreatmentIntent.PALLIATIVE,
        start_date=date(2024, 1, 15),
        end_date=date(2024, 6, 15),
        dose="80mg",
        route="oral",
    )
    data = med.model_dump()
    restored = MedicationExposure.model_validate(data)
    assert restored.drug_name == "Osimertinib"
    assert restored.modality == TreatmentModality.TARGETED_THERAPY


def test_procedure_radiation():
    proc = ProcedureEvent(
        procedure_id="PROC001",
        patient_id="P1",
        project_id="proj1",
        procedure_name="SBRT to lung",
        modality=TreatmentModality.RADIATION_SBRT,
        total_dose_gy=50.0,
        fractions=5,
        technique="VMAT",
        treatment_site="right lower lobe",
    )
    json_str = proc.model_dump_json()
    restored = ProcedureEvent.model_validate_json(json_str)
    assert restored.total_dose_gy == 50.0
    assert restored.fractions == 5
