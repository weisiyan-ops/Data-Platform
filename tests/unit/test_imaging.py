"""Tests for imaging models."""

from datetime import date

from app.models.enums import RECISTCategory
from app.models.imaging import ImagingReport, LesionMeasurement


def test_imaging_report_round_trip():
    report = ImagingReport(
        imaging_id="IMG001",
        patient_id="P1",
        project_id="proj1",
        study_date=date(2024, 6, 1),
        modality="CT",
        body_region="chest/abdomen/pelvis",
        recist_category=RECISTCategory.PR,
        sum_longest_diameters_mm=45.0,
        prior_sum_mm=60.0,
        percent_change=-25.0,
        new_lesions=False,
        lesions=[
            LesionMeasurement(
                lesion_id="L1",
                is_target=True,
                location="right lower lobe",
                longest_diameter_mm=25.0,
                prior_diameter_mm=35.0,
            ),
            LesionMeasurement(
                lesion_id="L2",
                is_target=True,
                location="liver segment 6",
                longest_diameter_mm=20.0,
                prior_diameter_mm=25.0,
            ),
        ],
    )
    json_str = report.model_dump_json()
    restored = ImagingReport.model_validate_json(json_str)
    assert restored.recist_category == RECISTCategory.PR
    assert len(restored.lesions) == 2
    assert restored.lesions[0].longest_diameter_mm == 25.0


def test_imaging_minimal():
    report = ImagingReport(imaging_id="IMG002", patient_id="P1", project_id="proj1")
    assert report.modality is None
    assert report.lesions == []
