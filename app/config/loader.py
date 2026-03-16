"""YAML loading with deep merge support."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base, returning a new dict.

    - Dicts are merged recursively.
    - Lists in override replace lists in base (no append).
    - Scalars in override replace scalars in base.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_merged_cancer_config(
    cancer_name: str, configs_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load _base.yaml and merge with cancer-specific config."""
    if configs_dir is None:
        configs_dir = Path(__file__).resolve().parent.parent.parent / "configs"
    configs_dir = Path(configs_dir)

    base_path = configs_dir / "cancers" / "_base.yaml"
    cancer_path = configs_dir / "cancers" / f"{cancer_name}.yaml"

    base = load_yaml(base_path) if base_path.exists() else {}
    if not cancer_path.exists():
        raise FileNotFoundError(f"Cancer config not found: {cancer_path}")
    cancer = load_yaml(cancer_path)

    return deep_merge(base, cancer)
