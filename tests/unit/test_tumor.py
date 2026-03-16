"""Tests for TumorAssessmentEvent model."""

from datetime import date

from app.models.enums import ClinicalStageGroup, Grade, StagingSystem
from app.models.tumor import TumorAssessmentEvent


def test_tumor_assessment_round_trip():
    t = TumorAssessmentEvent(
        assessment_id="TA001",
        patient_id="P1",
        project_id="proj1",
        clinical_t="T2",
        clinical_n="N1",
        clinical_m="M0",
        stage_group=ClinicalStageGroup.STAGE_IIIA,
        staging_system=StagingSystem.AJCC_8TH,
        grade=Grade.G2,
        tumor_size_cm=3.5,
        biomarkers={"EGFR": "positive", "PD-L1": 80.0},
    )
    json_str = t.model_dump_json()
    restored = TumorAssessmentEvent.model_validate_json(json_str)
    assert restored.stage_group == ClinicalStageGroup.STAGE_IIIA
    assert restored.biomarkers["EGFR"] == "positive"
    assert restored.tumor_size_cm == 3.5


def test_tumor_minimal():
    t = TumorAssessmentEvent(
        assessment_id="TA002", patient_id="P1", project_id="proj1"
    )
    assert t.clinical_t is None
    assert t.biomarkers is None
