"""Storage backend protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends. Implementations must provide these methods."""

    def initialize(self) -> None:
        """Create tables/schema if they don't exist."""
        ...

    def is_ready(self) -> bool:
        """Check if the backend is connected and ready."""
        ...

    def save_record(self, table: str, record: dict[str, Any]) -> None:
        """Insert or upsert a single record."""
        ...

    def get_record(self, table: str, record_id: str) -> dict[str, Any] | None:
        """Retrieve a single record by its primary key."""
        ...

    def list_records(
        self,
        table: str,
        project_id: str | None = None,
        patient_id: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List records with optional filtering."""
        ...

    def execute_sql(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Execute raw SQL and return results as dicts."""
        ...

    def export_csv(self, table: str, output_path: str, project_id: str | None = None) -> int:
        """Export a table to CSV. Returns row count."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...
