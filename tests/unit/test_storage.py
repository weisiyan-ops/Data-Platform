"""Storage backend tests — parametrized for both DuckDB and SQLite."""

import os
from pathlib import Path

from app.db.protocol import StorageBackend


def test_backend_is_ready(storage: StorageBackend):
    assert storage.is_ready()


def test_save_and_get_patient(storage: StorageBackend):
    record = {
        "patient_id": "P001",
        "project_id": "proj1",
        "sex": "male",
        "age_at_dx": 65,
    }
    storage.save_record("patients", record)
    result = storage.get_record("patients", "P001")
    assert result is not None
    assert result["patient_id"] == "P001"
    assert result["sex"] == "male"
    assert result["age_at_dx"] == 65


def test_save_and_list(storage: StorageBackend):
    for i in range(3):
        storage.save_record("patients", {
            "patient_id": f"P{i:03d}",
            "project_id": "proj1",
            "sex": "female",
        })
    results = storage.list_records("patients", project_id="proj1")
    assert len(results) == 3


def test_list_by_patient(storage: StorageBackend):
    storage.save_record("encounters", {
        "encounter_id": "E001",
        "patient_id": "P001",
        "project_id": "proj1",
    })
    storage.save_record("encounters", {
        "encounter_id": "E002",
        "patient_id": "P002",
        "project_id": "proj1",
    })
    results = storage.list_records("encounters", patient_id="P001")
    assert len(results) == 1
    assert results[0]["encounter_id"] == "E001"


def test_get_missing_record(storage: StorageBackend):
    result = storage.get_record("patients", "NONEXISTENT")
    assert result is None


def test_upsert(storage: StorageBackend):
    storage.save_record("patients", {
        "patient_id": "P001",
        "project_id": "proj1",
        "sex": "male",
    })
    storage.save_record("patients", {
        "patient_id": "P001",
        "project_id": "proj1",
        "sex": "female",
    })
    result = storage.get_record("patients", "P001")
    assert result["sex"] == "female"


def test_execute_sql(storage: StorageBackend):
    storage.save_record("patients", {
        "patient_id": "P001",
        "project_id": "proj1",
        "age_at_dx": 70,
    })
    rows = storage.execute_sql("SELECT patient_id, age_at_dx FROM patients WHERE age_at_dx > 60")
    assert len(rows) == 1
    assert rows[0]["age_at_dx"] == 70


def test_export_csv(storage: StorageBackend, tmp_path):
    storage.save_record("patients", {
        "patient_id": "P001",
        "project_id": "proj1",
        "sex": "male",
    })
    output_path = str(tmp_path / "export.csv")
    count = storage.export_csv("patients", output_path)
    assert count == 1
    assert Path(output_path).exists()
    content = Path(output_path).read_text()
    assert "P001" in content
