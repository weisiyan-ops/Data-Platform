"""ProvenanceRecord — rich evidence wrapper for every extracted field."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ConfidenceTier, ExtractionMethod, ReviewStatus


class ProvenanceRecord(BaseModel):
    """Tracks the origin and confidence of a single extracted field value."""

    field_name: str
    field_value: str | int | float | bool | None = None
    value_type: str = "str"  # "str", "int", "float", "date", "bool", "enum"

    # Source identification
    source_adapter: str  # "epic_fhir", "china_images", etc.
    source_resource_type: str | None = None  # "Condition", "DocumentReference"
    source_resource_id: str | None = None
    source_doc_id: str | None = None
    encounter_id: str | None = None

    # Location within source
    doc_datetime: datetime | None = None
    page_no: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    # Evidence
    evidence_text: str | None = None
    normalized_text: str | None = None

    # Quality
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier | None = None
    extraction_method: ExtractionMethod | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None

    model_config = {"frozen": False}
