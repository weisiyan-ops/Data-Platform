"""Tests for DerivedEndpoints model."""

from datetime import date

from app.models.timeline import DerivedEndpoints


def test_derived_endpoints_round_trip():
    ep = DerivedEndpoints(
        endpoint_id="EP001",
        patient_id="P1",
        project_id="proj1",
        index_date=date(2024, 1, 15),
        index_date_definition="start_of_treatment",
        os_months=12.5,
        os_event=True,
        pfs_months=8.2,
        pfs_event=True,
        pfs_event_type="progression",
        pfs_event_date=date(2024, 9, 20),
        lc_months=12.5,
        lc_event=False,
    )
    json_str = ep.model_dump_json()
    restored = DerivedEndpoints.model_validate_json(json_str)
    assert restored.os_months == 12.5
    assert restored.pfs_event is True
    assert restored.lc_event is False


def test_derived_endpoints_censored():
    ep = DerivedEndpoints(
        endpoint_id="EP002",
        patient_id="P2",
        project_id="proj1",
        os_event=False,
        os_censor_date=date(2024, 12, 31),
        os_censor_reason="last_contact",
        pfs_event=False,
    )
    assert ep.os_event is False
    assert ep.os_censor_reason == "last_contact"
