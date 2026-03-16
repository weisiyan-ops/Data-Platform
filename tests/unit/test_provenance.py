"""Tests for ProvenanceRecord."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.enums import ConfidenceTier, ExtractionMethod, ReviewStatus
from app.models.provenance import ProvenanceRecord


def test_provenance_round_trip():
    rec = ProvenanceRecord(
        field_name="stage_group",
        field_value="IIIA",
        value_type="enum",
        source_adapter="epic_fhir",
        confidence=0.85,
        confidence_tier=ConfidenceTier.MEDIUM,
        extraction_method=ExtractionMethod.NLP,
        evidence_text="The patient was staged as IIIA.",
    )
    data = rec.model_dump()
    restored = ProvenanceRecord.model_validate(data)
    assert restored.field_name == "stage_group"
    assert restored.confidence == 0.85
    assert restored.confidence_tier == ConfidenceTier.MEDIUM


def test_provenance_json_round_trip():
    rec = ProvenanceRecord(
        field_name="sex",
        field_value="male",
        value_type="enum",
        source_adapter="china_images",
        bbox=(10.0, 20.0, 100.0, 50.0),
        page_no=1,
    )
    json_str = rec.model_dump_json()
    restored = ProvenanceRecord.model_validate_json(json_str)
    assert restored.bbox == (10.0, 20.0, 100.0, 50.0)
    assert restored.page_no == 1


def test_confidence_bounds():
    with pytest.raises(ValidationError):
        ProvenanceRecord(
            field_name="x",
            source_adapter="test",
            confidence=1.5,
        )

    with pytest.raises(ValidationError):
        ProvenanceRecord(
            field_name="x",
            source_adapter="test",
            confidence=-0.1,
        )


def test_confidence_null_allowed():
    rec = ProvenanceRecord(
        field_name="x",
        source_adapter="test",
        confidence=None,
    )
    assert rec.confidence is None


def test_review_status_default():
    rec = ProvenanceRecord(field_name="x", source_adapter="test")
    assert rec.review_status == ReviewStatus.UNREVIEWED


def test_all_fields_populated():
    rec = ProvenanceRecord(
        field_name="diagnosis_date",
        field_value="2024-03-15",
        value_type="date",
        source_adapter="epic_ccda",
        source_resource_type="Condition",
        source_resource_id="Condition/456",
        source_doc_id="doc_789",
        encounter_id="enc_001",
        doc_datetime=datetime(2024, 3, 15, 10, 30),
        page_no=2,
        char_start=100,
        char_end=110,
        bbox=(0.0, 0.0, 1.0, 1.0),
        evidence_text="Diagnosis: 2024-03-15",
        normalized_text="2024-03-15",
        confidence=1.0,
        confidence_tier=ConfidenceTier.HIGH,
        extraction_method=ExtractionMethod.STRUCTURED,
        review_status=ReviewStatus.ACCEPTED,
        reviewer_id="reviewer_a",
        reviewed_at=datetime(2024, 4, 1, 12, 0),
    )
    assert rec.char_start == 100
    assert rec.reviewer_id == "reviewer_a"
