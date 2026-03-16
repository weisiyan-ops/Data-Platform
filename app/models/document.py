"""Source document models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DocumentType
from app.models.provenance import ProvenanceRecord


class PageInfo(BaseModel):
    """Metadata for a single page within a document."""

    page_no: int
    width: float | None = None
    height: float | None = None
    ocr_text: str | None = None
    ocr_confidence: float | None = None
    language: str | None = None


class SourceDocument(BaseModel):
    """A raw source document (file, image, PDF, etc.)."""

    doc_id: str
    patient_id: str
    project_id: str
    file_path: str | None = None
    file_hash: str | None = None
    mime_type: str | None = None
    page_count: int | None = None
    pages: list[PageInfo] = []
    ingested_at: datetime | None = None

    provenance: list[ProvenanceRecord] = []


class ClinicalNote(BaseModel):
    """A clinical note extracted from a source document or EHR."""

    note_id: str
    patient_id: str
    project_id: str
    encounter_id: str | None = None
    source_doc_id: str | None = None
    document_type: DocumentType | None = None
    note_datetime: datetime | None = None
    author: str | None = None
    original_text: str | None = None
    translated_text: str | None = None
    language: str | None = None
    sections: dict[str, str] | None = None  # section_name -> text

    provenance: list[ProvenanceRecord] = []
