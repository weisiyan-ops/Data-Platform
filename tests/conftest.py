"""Shared test fixtures."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.db import create_backend
from app.db.protocol import StorageBackend
from app.models.enums import (
    CancerType,
    ConfidenceTier,
    ExtractionMethod,
    ReviewStatus,
    Sex,
)
from app.models.patient import Patient
from app.models.provenance import ProvenanceRecord


@pytest.fixture(params=["sqlite", "duckdb"])
def storage(request: pytest.FixtureRequest, tmp_path) -> StorageBackend:
    """Parametrized storage backend fixture — runs tests against both backends."""
    backend_type = request.param
    db_path = str(tmp_path / f"test.{backend_type}")
    backend = create_backend(backend_type, db_path)
    backend.initialize()
    yield backend
    backend.close()


@pytest.fixture
def sample_provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        field_name="sex",
        field_value="male",
        value_type="enum",
        source_adapter="epic_fhir",
        source_resource_type="Patient",
        source_resource_id="Patient/123",
        confidence=0.95,
        confidence_tier=ConfidenceTier.HIGH,
        extraction_method=ExtractionMethod.STRUCTURED,
        review_status=ReviewStatus.UNREVIEWED,
        evidence_text="Sex: Male",
    )


@pytest.fixture
def sample_patient(sample_provenance: ProvenanceRecord) -> Patient:
    return Patient(
        patient_id="PT001",
        project_id="test_project",
        sex=Sex.MALE,
        age_at_dx=65,
        diagnosis_date=date(2024, 3, 15),
        provenance=[sample_provenance],
    )
