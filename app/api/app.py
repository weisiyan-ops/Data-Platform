"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routers import export, health, patients, pipeline, projects


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Oncology Data Extraction Platform",
        description="Research-oriented oncology data abstraction API",
        version="0.1.0",
    )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(patients.router)
    app.include_router(pipeline.router)
    app.include_router(export.router)

    return app
