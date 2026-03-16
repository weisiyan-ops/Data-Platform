"""Tests for enums."""

from app.models.enums import (
    CancerType,
    ClinicalStageGroup,
    ConfidenceTier,
    Grade,
    RECISTCategory,
    ReviewStatus,
    Sex,
    TreatmentModality,
    VitalStatus,
)


def test_sex_values():
    assert Sex.MALE.value == "male"
    assert Sex.FEMALE.value == "female"
    assert Sex("male") == Sex.MALE


def test_cancer_type_values():
    assert CancerType.LUNG.value == "lung"
    assert CancerType.BREAST.value == "breast"


def test_recist_categories():
    assert RECISTCategory.CR.value == "CR"
    assert RECISTCategory.PD.value == "PD"


def test_stage_groups():
    assert ClinicalStageGroup.STAGE_IIIA.value == "IIIA"
    assert ClinicalStageGroup.STAGE_IV.value == "IV"


def test_confidence_tiers():
    assert ConfidenceTier.HIGH.value == "high"
    assert ConfidenceTier.LOW.value == "low"


def test_grade_values():
    assert Grade.G1.value == "G1"
    assert Grade.GX.value == "GX"


def test_treatment_modality():
    assert TreatmentModality.RADIATION_SBRT.value == "radiation_sbrt"


def test_vital_status():
    assert VitalStatus.DECEASED.value == "deceased"


def test_review_status():
    assert ReviewStatus.CORRECTED.value == "corrected"
