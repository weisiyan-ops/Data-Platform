"""Tests for progression and response models."""

from datetime import date

from app.models.enums import ProgressionType, RECISTCategory
from app.models.progression import ProgressionEvent, ResponseEvent


def test_progression_event():
    pe = ProgressionEvent(
        progression_id="PG001",
        patient_id="P1",
        project_id="proj1",
        event_date=date(2024, 9, 1),
        progression_type=ProgressionType.DISTANT,
        site="brain",
        detection_method="imaging",
    )
    data = pe.model_dump()
    restored = ProgressionEvent.model_validate(data)
    assert restored.progression_type == ProgressionType.DISTANT
    assert restored.site == "brain"


def test_response_event():
    re = ResponseEvent(
        response_id="RE001",
        patient_id="P1",
        project_id="proj1",
        best_response=RECISTCategory.PR,
        treatment_line=1,
    )
    assert re.best_response == RECISTCategory.PR
