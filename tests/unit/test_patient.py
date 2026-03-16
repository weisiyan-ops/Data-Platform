"""Tests for Patient model."""

from datetime import date

from app.models.enums import Sex
from app.models.patient import Patient
from app.models.provenance import ProvenanceRecord


def test_patient_minimal():
    p = Patient(patient_id="P1", project_id="proj1")
    assert p.patient_id == "P1"
    assert p.sex is None
    assert p.provenance == []


def test_patient_full(sample_patient):
    assert sample_patient.sex == Sex.MALE
    assert sample_patient.age_at_dx == 65
    assert sample_patient.diagnosis_date == date(2024, 3, 15)
    assert len(sample_patient.provenance) == 1


def test_patient_json_round_trip(sample_patient):
    json_str = sample_patient.model_dump_json()
    restored = Patient.model_validate_json(json_str)
    assert restored.patient_id == sample_patient.patient_id
    assert restored.sex == sample_patient.sex
    assert len(restored.provenance) == 1


def test_patient_null_fields():
    p = Patient(patient_id="P2", project_id="proj1")
    assert p.death_date is None
    assert p.kps is None
    assert p.smoking_status is None
