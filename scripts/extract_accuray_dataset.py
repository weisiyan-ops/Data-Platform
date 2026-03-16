"""Build a merged Accuray CSV from SCART, blood work, chart OCR, and radiology files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.accuray_helpers import (
    SECTION_KEYS,
    extract_chart_sections,
    extract_name_from_chart_stem,
    normalize_patient_name,
)


DEFAULT_BASE_DIR = Path("/mnt/c/Users/wya245/Dropbox/Accuray")
FOLLOWUP_BLOCK_RE = re.compile(r"^(复查(?:时间|结果|备注|filename)\s*\d+)$")
SIZE_BLOCK_RE = re.compile(r"^(复查(?:时间|结果|备注)\d+|尺寸\d+)$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BASE_DIR / "HCC_SCART_extracted_with_chart_ocr.csv",
    )
    return parser


def load_base_cases(base_dir: Path) -> pd.DataFrame:
    df = pd.read_excel(base_dir / "SCART 03092026.xlsx", sheet_name="生存数据")
    df.columns = [str(col).strip() for col in df.columns]
    df["patient_name_normalized"] = df["中文名"].map(normalize_patient_name)
    df["scart_start_date_parsed"] = pd.to_datetime(df.get("SCART治疗日期"), errors="coerce")
    df["scart_end_date_parsed"] = pd.to_datetime(df.get("末次SCART日期"), errors="coerce")
    return df


def load_lab_summary(base_dir: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    blood_dir = base_dir / "Blood Work"

    for path in sorted(blood_dir.glob("*.xlsx")):
        patient_name = normalize_patient_name(path.stem)
        workbook = pd.ExcelFile(path)
        row: dict[str, Any] = {
            "patient_name_normalized": patient_name,
            "blood_work_file": path.name,
        }

        for sheet_name in workbook.sheet_names:
            if sheet_name.lower() == "sheet":
                continue
            analyte_key = str(sheet_name).strip()
            df = pd.read_excel(path, sheet_name=sheet_name)
            df = df.rename(columns=lambda col: str(col).strip())
            if "日期" not in df.columns or "结果" not in df.columns:
                continue

            df = df[["结果", "日期"]].copy()
            df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
            df["结果"] = df["结果"].astype(str).str.strip()
            df = df[df["日期"].notna() & df["结果"].ne("") & df["结果"].ne("nan")]
            if df.empty:
                continue

            df = df.sort_values("日期")
            earliest = df.iloc[0]
            latest = df.iloc[-1]
            prefix = f"lab_{analyte_key}"
            row[f"{prefix}_baseline_value"] = earliest["结果"]
            row[f"{prefix}_baseline_date"] = earliest["日期"]
            row[f"{prefix}_latest_value"] = latest["结果"]
            row[f"{prefix}_latest_date"] = latest["日期"]
            row[f"{prefix}_count"] = int(len(df))

        records.append(row)

    if not records:
        return pd.DataFrame(columns=["patient_name_normalized"])
    return pd.DataFrame(records).drop_duplicates(subset=["patient_name_normalized"], keep="first")


def _ocr_lines_for_image(ocr_engine: Any, image_path: Path) -> list[str]:
    result, _ = ocr_engine(str(image_path))
    if not result:
        return []

    sorted_items = sorted(
        result,
        key=lambda item: (
            min(point[1] for point in item[0]),
            min(point[0] for point in item[0]),
        ),
    )
    return [str(item[1]).strip() for item in sorted_items if str(item[1]).strip()]


def load_chart_history(base_dir: Path) -> pd.DataFrame:
    from rapidocr_onnxruntime import RapidOCR  # Imported lazily so tests don't require OCR.

    ocr_engine = RapidOCR()
    records: list[dict[str, Any]] = []
    chart_dir = base_dir / "HIstory from Chart"

    for path in sorted(chart_dir.glob("*.png")):
        patient_name = extract_name_from_chart_stem(path.stem)
        lines = _ocr_lines_for_image(ocr_engine, path)
        sections = extract_chart_sections(lines)
        records.append(
            {
                "patient_name_normalized": patient_name,
                "chart_history_image_file": path.name,
                "chart_history_file_date": _extract_filename_date(path.stem),
                "chart_ocr_text": "\n".join(lines) if lines else None,
                **{f"chart_{key}": sections[key] for key in SECTION_KEYS},
            }
        )

    if not records:
        return pd.DataFrame(columns=["patient_name_normalized"])
    return pd.DataFrame(records).drop_duplicates(subset=["patient_name_normalized"], keep="first")


def _extract_filename_date(stem: str) -> str | None:
    match = re.search(r"(\d{4}(?:-\d{2}(?:-\d{2})?)?)$", stem)
    return match.group(1) if match else None


def load_radiology(base_dir: Path) -> pd.DataFrame:
    path = base_dir / "Radiology Data" / "影像结果.xlsx"
    df = pd.read_excel(path)
    df.columns = [str(col).strip() for col in df.columns]
    df["patient_name_normalized"] = df["中文名"].map(normalize_patient_name)
    df["radiology_放疗时间"] = pd.to_datetime(df.get("放疗时间"), errors="coerce")

    keep_columns = ["patient_name_normalized", "radiology_放疗时间"]
    renamed: dict[str, str] = {}
    for column in df.columns:
        if column in {"中文名", "放疗时间", "patient_name_normalized"}:
            continue
        if (
            column == "放疗截图filename"
            or FOLLOWUP_BLOCK_RE.match(column)
            or SIZE_BLOCK_RE.match(column)
        ):
            renamed[column] = f"radiology_{column}"
            keep_columns.append(column)

    df = df[["patient_name_normalized", "radiology_放疗时间", *renamed.keys()]].rename(columns=renamed)
    return df


def merge_radiology(base_df: pd.DataFrame, radiology_df: pd.DataFrame) -> pd.DataFrame:
    radiology_columns = [col for col in radiology_df.columns if col != "patient_name_normalized"]
    merged_rows: list[dict[str, Any]] = []

    for _, base_row in base_df.iterrows():
        patient_name = base_row["patient_name_normalized"]
        candidates = radiology_df[radiology_df["patient_name_normalized"] == patient_name].copy()
        row_data = {column: pd.NA for column in radiology_columns}

        if not candidates.empty:
            reference_date = base_row.get("scart_start_date_parsed")
            if pd.isna(reference_date):
                reference_date = base_row.get("scart_end_date_parsed")

            if pd.notna(reference_date):
                candidates["_delta_days"] = (
                    candidates["radiology_放疗时间"] - reference_date
                ).abs().dt.days
                candidates = candidates.sort_values(
                    by=["_delta_days", "radiology_放疗时间"], na_position="last"
                )
            else:
                candidates = candidates.sort_values(by=["radiology_放疗时间"], na_position="last")

            best = candidates.iloc[0].to_dict()
            for column in radiology_columns:
                row_data[column] = best.get(column, pd.NA)

        merged_rows.append(row_data)

    radiology_matched = pd.DataFrame(merged_rows)
    return pd.concat([base_df.reset_index(drop=True), radiology_matched], axis=1)


def build_dataset(base_dir: Path) -> pd.DataFrame:
    base_df = load_base_cases(base_dir)
    lab_df = load_lab_summary(base_dir)
    chart_df = load_chart_history(base_dir)
    radiology_df = load_radiology(base_dir)

    merged = base_df.merge(lab_df, on="patient_name_normalized", how="left")
    merged = merged.merge(chart_df, on="patient_name_normalized", how="left")
    merged = merge_radiology(merged, radiology_df)
    return merged.drop(columns=["patient_name_normalized", "scart_start_date_parsed", "scart_end_date_parsed"])


def main() -> None:
    args = build_parser().parse_args()
    df = build_dataset(args.base_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} rows and {len(df.columns)} columns to {args.output}")


if __name__ == "__main__":
    main()
