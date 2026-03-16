"""Application settings via pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class StorageSettings(BaseSettings):
    backend: str = "duckdb"  # "duckdb" or "sqlite"
    database_path: str = "data/onco.duckdb"


class LoggingSettings(BaseSettings):
    level: str = "INFO"
    format: str = "json"  # "json" or "text"


class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class AppSettings(BaseSettings):
    """Top-level application settings. Can be overridden via env vars prefixed ONCO_."""

    model_config = {"env_prefix": "ONCO_", "env_nested_delimiter": "__"}

    app_name: str = "onco-extractor"
    version: str = "0.1.0"
    debug: bool = False
    configs_dir: str = "configs"
    projects_dir: str = "projects"
    storage: StorageSettings = Field(default_factory=StorageSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)


def get_settings() -> AppSettings:
    """Factory function for AppSettings."""
    return AppSettings()
