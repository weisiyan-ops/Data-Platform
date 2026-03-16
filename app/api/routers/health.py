"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings, get_storage
from app.config.settings import AppSettings
from app.db.protocol import StorageBackend

router = APIRouter()


@router.get("/health")
def health(settings: AppSettings = Depends(get_app_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
    }


@router.get("/ready")
def ready(storage: StorageBackend = Depends(get_storage)) -> dict:
    is_ready = storage.is_ready()
    return {
        "ready": is_ready,
    }
