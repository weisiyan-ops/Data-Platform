"""Input adapter protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.models.patient import Patient


@runtime_checkable
class InputAdapter(Protocol):
    """Protocol for input adapters that ingest data from various sources."""

    adapter_name: str

    def can_handle(self, source_path: str) -> bool:
        """Check if this adapter can handle the given source."""
        ...

    def ingest(self, source_path: str, project_id: str) -> list[Patient]:
        """Ingest data from source and return patient records."""
        ...

    def get_metadata(self) -> dict[str, Any]:
        """Return metadata about this adapter."""
        ...
