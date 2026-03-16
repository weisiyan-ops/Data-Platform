"""Tests for LabResult model."""

from datetime import datetime

from app.models.lab import LabResult


def test_lab_round_trip():
    lab = LabResult(
        lab_id="LAB001",
        patient_id="P1",
        project_id="proj1",
        analyte_name="hemoglobin",
        analyte_code="718-7",
        code_system="LOINC",
        value_numeric=12.5,
        unit="g/dL",
        reference_low=12.0,
        reference_high=16.0,
        abnormal_flag="N",
        collection_datetime=datetime(2024, 3, 15, 8, 0),
    )
    data = lab.model_dump()
    restored = LabResult.model_validate(data)
    assert restored.value_numeric == 12.5
    assert restored.unit == "g/dL"


def test_lab_text_value():
    lab = LabResult(
        lab_id="LAB002",
        patient_id="P1",
        project_id="proj1",
        analyte_name="EGFR mutation",
        value_text="L858R positive",
    )
    assert lab.value_numeric is None
    assert lab.value_text == "L858R positive"
