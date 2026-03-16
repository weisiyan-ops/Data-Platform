"""Helpers for matching Accuray patient data and parsing OCR'd chart sections."""

from __future__ import annotations

import re
from collections.abc import Iterable


NAME_ALIASES: dict[str, str] = {
    "叶立葵": "叶立奎",
}

SECTION_LABELS: list[tuple[str, tuple[str, ...]]] = [
    ("chief_complaint", ("主诉",)),
    ("present_illness", ("现病史",)),
    ("past_history", ("既往史",)),
    ("personal_history", ("个人史",)),
    ("marital_history", ("婚育史",)),
    ("menstrual_history", ("月经史",)),
    ("family_history", ("家族史",)),
    ("specialist_exam", ("专科情况", "体格检查")),
    ("preliminary_diagnosis", ("初步诊断",)),
]

SECTION_KEYS: tuple[str, ...] = tuple(key for key, _labels in SECTION_LABELS)

_SEPARATOR_RE = re.compile(r"[\s\u3000]+")
_DATE_SUFFIX_RE = re.compile(r"\s+\d{4}(?:-\d{2}(?:-\d{2})?)?$")


def normalize_patient_name(value: str | None) -> str:
    """Normalize patient names across spreadsheets and filenames."""
    if value is None:
        return ""

    cleaned = value.replace(" - Copy", "").strip()
    cleaned = _SEPARATOR_RE.sub("", cleaned)
    return NAME_ALIASES.get(cleaned, cleaned)


def extract_name_from_chart_stem(stem: str) -> str:
    """Extract the patient name from a chart screenshot filename stem."""
    return normalize_patient_name(_DATE_SUFFIX_RE.sub("", stem))


def split_label_and_value(line: str) -> tuple[str | None, str | None]:
    """Detect whether a single OCR line begins a known chart section."""
    stripped = line.strip()
    if not stripped:
        return None, None

    compact = stripped.replace("：", ":")
    for key, labels in SECTION_LABELS:
        for label in labels:
            if compact == label:
                return key, None
            prefix = f"{label}:"
            if compact.startswith(prefix):
                value = compact[len(prefix):].strip()
                return key, value or None
    return None, None


def extract_chart_sections(lines: Iterable[str]) -> dict[str, str | None]:
    """Group OCR lines into chart history sections."""
    sections: dict[str, list[str]] = {key: [] for key in SECTION_KEYS}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        new_key, inline_value = split_label_and_value(line)
        if new_key is not None:
            current_key = new_key
            if inline_value:
                sections[current_key].append(inline_value)
            continue

        if current_key is not None:
            sections[current_key].append(line)

    return {
        key: "\n".join(value_lines).strip() if value_lines else None
        for key, value_lines in sections.items()
    }

