"""Tests for config system."""

from pathlib import Path

import pytest

from app.config.cancer_config import CancerConfig, load_cancer_config
from app.config.loader import deep_merge, load_yaml
from app.config.settings import AppSettings


CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


def test_deep_merge_basic():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99, "e": 5}, "f": 6}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3, "e": 5}, "f": 6}


def test_deep_merge_list_replaces():
    base = {"items": [1, 2, 3]}
    override = {"items": [4, 5]}
    result = deep_merge(base, override)
    assert result["items"] == [4, 5]


def test_deep_merge_no_mutation():
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    result = deep_merge(base, override)
    assert "c" not in base["a"]


def test_load_yaml(tmp_path):
    f = tmp_path / "test.yaml"
    f.write_text("key: value\nnested:\n  a: 1\n")
    data = load_yaml(f)
    assert data["key"] == "value"
    assert data["nested"]["a"] == 1


def test_load_yaml_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_yaml(tmp_path / "missing.yaml")


def test_load_base_config():
    data = load_yaml(CONFIGS_DIR / "cancers" / "_base.yaml")
    assert "lab_analytes" in data
    assert "progression_keywords" in data


def test_load_lung_config():
    config = load_cancer_config("lung", str(CONFIGS_DIR))
    assert config.cancer_type == "lung"
    assert "EGFR" in config.biomarkers
    assert len(config.histology_keywords) > 0


def test_load_breast_config():
    config = load_cancer_config("breast", str(CONFIGS_DIR))
    assert config.cancer_type == "breast"
    assert "ER" in config.biomarkers


def test_lung_inherits_base_lab_analytes():
    config = load_cancer_config("lung", str(CONFIGS_DIR))
    # Lung doesn't override lab_analytes, so should get base's
    assert "hemoglobin" in config.lab_analytes


def test_missing_cancer_config():
    with pytest.raises(FileNotFoundError):
        load_cancer_config("nonexistent_cancer", str(CONFIGS_DIR))


def test_app_settings_defaults():
    settings = AppSettings()
    assert settings.app_name == "onco-extractor"
    assert settings.storage.backend == "duckdb"
    assert settings.api.port == 8000


def test_all_cancer_configs_valid():
    """Ensure every cancer YAML in configs/cancers validates."""
    cancer_dir = CONFIGS_DIR / "cancers"
    for yaml_file in cancer_dir.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        config = load_cancer_config(yaml_file.stem, str(CONFIGS_DIR))
        assert config.cancer_type == yaml_file.stem
