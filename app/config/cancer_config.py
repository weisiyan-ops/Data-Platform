"""Cancer-specific configuration model and loader."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.config.loader import load_merged_cancer_config


class StageMapping(BaseModel):
    system: str = "AJCC_8th"
    aliases: dict[str, str] = {}


class CancerConfig(BaseModel):
    """Validated cancer-specific configuration."""

    cancer_type: str
    display_name: str = ""
    histology_keywords: list[str] = []
    staging: StageMapping = StageMapping()
    primary_site_keywords: list[str] = []
    treatment_keywords: dict[str, list[str]] = {}
    biomarkers: list[str] = []
    lab_analytes: list[str] = []
    progression_keywords: list[str] = []
    response_keywords: list[str] = []
    extra: dict[str, Any] = {}


def load_cancer_config(
    cancer_name: str, configs_dir: str | None = None
) -> CancerConfig:
    """Load and validate a cancer config from YAML."""
    raw = load_merged_cancer_config(cancer_name, configs_dir)
    raw.setdefault("cancer_type", cancer_name)
    return CancerConfig.model_validate(raw)
