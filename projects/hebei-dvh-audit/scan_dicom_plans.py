#!/usr/bin/env python
"""
HeBei DICOM RT Plan Scanner
============================
Scans all patient DICOM folders and reports RT Plan metadata.
This helps us understand which plans are treatment vs QA/verification.

Usage:
    python scan_dicom_plans.py <dicom_root_dir> [output_csv]

Example:
    python scan_dicom_plans.py D:\VSproject\ICE3-V2.0-main\yan_data\DICOM60
    python scan_dicom_plans.py D:\VSproject\ICE3-V2.0-main\yan_data\DICOM60 plan_report.csv

Output: CSV file with one row per RT Plan file found.
"""

import os
import sys
import csv
import glob

try:
    import pydicom
except ImportError:
    print("ERROR: pydicom not installed. Run: pip install pydicom")
    sys.exit(1)


TAGS_TO_READ = [
    ("PatientID", "PatientID"),
    ("PatientName", "PatientName"),
    ("RTPlanLabel", "RTPlanLabel"),
    ("RTPlanName", "RTPlanName"),
    ("PlanIntent", "PlanIntent"),
    ("RTPlanDescription", "RTPlanDescription"),
    ("RTPlanDate", "RTPlanDate"),
    ("RTPlanTime", "RTPlanTime"),
    ("Manufacturer", "Manufacturer"),
    ("ManufacturerModelName", "ManufacturerModelName"),
    ("SOPInstanceUID", "SOPInstanceUID"),
    ("ReferencedStructureSetSequence", "_has_struct_ref"),
    ("DoseReferenceSequence", "_has_dose_ref"),
    ("FractionGroupSequence", "_fraction_info"),
    ("BeamSequence", "_beam_count"),
]


def safe_get(ds, attr):
    """Safely read a DICOM attribute."""
    try:
        val = getattr(ds, attr, None)
        if val is None:
            return ""
        return str(val).strip()
    except Exception:
        return ""


def extract_fraction_info(ds):
    """Extract fraction count and planned dose from FractionGroupSequence."""
    try:
        fgs = ds.FractionGroupSequence
        if fgs and len(fgs) > 0:
            fg = fgs[0]
            n_fx = getattr(fg, "NumberOfFractionsPlanned", "")
            n_beams = getattr(fg, "NumberOfBeams", "")
            return str(n_fx), str(n_beams)
    except Exception:
        pass
    return "", ""


def extract_beam_count(ds):
    """Count beams in BeamSequence."""
    try:
        bs = ds.BeamSequence
        if bs:
            return str(len(bs))
    except Exception:
        pass
    return ""


def scan_patient_dir(patient_dir):
    """Scan a single patient directory for RT Plan files."""
    results = []
    for root, dirs, files in os.walk(patient_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if not fname.lower().endswith(".dcm") and "." in fname:
                ext = fname.rsplit(".", 1)[-1].lower()
                if ext not in ("dcm", ""):
                    continue
            try:
                ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
                modality = safe_get(ds, "Modality")
                if modality != "RTPLAN":
                    continue

                row = {
                    "patient_folder": os.path.basename(patient_dir),
                    "file_path": os.path.relpath(fpath, patient_dir),
                }
                for attr, label in TAGS_TO_READ:
                    if label == "_has_struct_ref":
                        row["has_struct_ref"] = "Yes" if getattr(ds, attr, None) else "No"
                    elif label == "_has_dose_ref":
                        row["has_dose_ref"] = "Yes" if getattr(ds, attr, None) else "No"
                    elif label == "_fraction_info":
                        n_fx, n_beams_fg = extract_fraction_info(ds)
                        row["n_fractions_planned"] = n_fx
                        row["n_beams_in_fraction_group"] = n_beams_fg
                    elif label == "_beam_count":
                        row["beam_count"] = extract_beam_count(ds)
                    else:
                        row[label] = safe_get(ds, attr)

                # Also check for RT Dose files referencing this plan
                row["sop_uid"] = safe_get(ds, "SOPInstanceUID")

                results.append(row)
            except Exception:
                continue
    return results


def count_dose_files_per_plan(patient_dir):
    """Map ReferencedRTPlanSequence SOPInstanceUID -> count of RT Dose files."""
    dose_map = {}
    for root, dirs, files in os.walk(patient_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
                if safe_get(ds, "Modality") != "RTDOSE":
                    continue
                ref_plan_seq = getattr(ds, "ReferencedRTPlanSequence", None)
                if ref_plan_seq and len(ref_plan_seq) > 0:
                    ref_uid = safe_get(ref_plan_seq[0], "ReferencedSOPInstanceUID")
                    if ref_uid:
                        dose_map[ref_uid] = dose_map.get(ref_uid, 0) + 1
            except Exception:
                continue
    return dose_map


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    dicom_root = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "hebei_plan_report.csv"

    if not os.path.isdir(dicom_root):
        print("ERROR: Directory not found: %s" % dicom_root)
        sys.exit(1)

    patient_dirs = sorted([
        os.path.join(dicom_root, d)
        for d in os.listdir(dicom_root)
        if os.path.isdir(os.path.join(dicom_root, d))
    ])

    print("Scanning %d patient folders in: %s" % (len(patient_dirs), dicom_root))

    all_rows = []
    for i, pdir in enumerate(patient_dirs):
        pname = os.path.basename(pdir)
        print("  [%d/%d] %s ..." % (i + 1, len(patient_dirs), pname), end="")

        plans = scan_patient_dir(pdir)
        dose_map = count_dose_files_per_plan(pdir)

        for plan in plans:
            uid = plan.get("sop_uid", "")
            plan["n_dose_files_referencing"] = dose_map.get(uid, 0)

        all_rows.extend(plans)
        print(" %d RT Plans found" % len(plans))

    if not all_rows:
        print("\nNo RT Plan files found!")
        sys.exit(1)

    fieldnames = [
        "patient_folder", "file_path", "RTPlanLabel", "RTPlanName",
        "PlanIntent", "RTPlanDescription", "RTPlanDate", "RTPlanTime",
        "n_fractions_planned", "beam_count", "n_beams_in_fraction_group",
        "has_struct_ref", "has_dose_ref", "n_dose_files_referencing",
        "Manufacturer", "ManufacturerModelName",
        "PatientID", "PatientName", "SOPInstanceUID",
    ]

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n" + "=" * 60)
    print("DONE: %d RT Plans across %d patients" % (len(all_rows), len(patient_dirs)))
    print("Report saved to: %s" % os.path.abspath(output_csv))
    print("=" * 60)

    # Print summary statistics
    labels = set()
    intents = set()
    for r in all_rows:
        if r.get("RTPlanLabel"):
            labels.add(r["RTPlanLabel"])
        if r.get("PlanIntent"):
            intents.add(r["PlanIntent"])

    print("\nUnique RTPlanLabel values found: %d" % len(labels))
    for lb in sorted(labels)[:30]:
        print("  - %s" % lb)

    print("\nUnique PlanIntent values found: %d" % len(intents))
    for pi in sorted(intents):
        print("  - %s" % pi)

    plans_per_patient = {}
    for r in all_rows:
        pf = r["patient_folder"]
        plans_per_patient[pf] = plans_per_patient.get(pf, 0) + 1

    counts = sorted(plans_per_patient.values())
    print("\nPlans per patient: min=%d, median=%d, max=%d" % (
        counts[0], counts[len(counts) // 2], counts[-1]))


if __name__ == "__main__":
    main()
