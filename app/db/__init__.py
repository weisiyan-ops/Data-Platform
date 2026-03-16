"""Storage backend factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.protocol import StorageBackend


def create_backend(backend_type: str = "duckdb", database_path: str = ":memory:") -> StorageBackend:
    """Create a storage backend instance.

    Args:
        backend_type: "duckdb" or "sqlite"
        database_path: Path to database file, or ":memory:" for in-memory.
    """
    if backend_type == "sqlite":
        from app.db.sqlite_backend import SQLiteBackend

        return SQLiteBackend(database_path)
    elif backend_type == "duckdb":
        from app.db.duckdb_backend import DuckDBBackend

        return DuckDBBackend(database_path)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}. Use 'duckdb' or 'sqlite'.")
