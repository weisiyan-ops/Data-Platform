"""FastAPI dependency injection."""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import AppSettings, get_settings
from app.db import create_backend
from app.db.protocol import StorageBackend


@lru_cache
def get_app_settings() -> AppSettings:
    return get_settings()


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Get or create the storage backend singleton."""
    global _backend
    if _backend is None:
        settings = get_app_settings()
        _backend = create_backend(
            backend_type=settings.storage.backend,
            database_path=settings.storage.database_path,
        )
        _backend.initialize()
    return _backend


def reset_storage() -> None:
    """Reset the storage singleton (for testing)."""
    global _backend
    if _backend is not None:
        _backend.close()
    _backend = None
