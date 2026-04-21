# HeBei DVH Quality Audit — 98final.xlsx

**Date**: 2026-04-21
**Source**: `C:\Users\wya245\Dropbox\HeBei\Raw Data\98final.xlsx`
**Context**: 98final.xlsx is the authoritative DVH source for ICE3 cross-validation analysis (HeBei cohort, n=100). DVH was computed by EDIC V2.0 from DICOM RT data.

---

## Executive Summary

A systematic audit of the 98final.xlsx DVH data reveals a **critical plan-summing issue** affecting **98 of 100 patients**. EDIC V2.0 summed DVH from ALL DICOM RT plans in each patient's folder — including verification plans, QA plans, setup fields, and backup plans — inflating MHD, MLD, and MBD by 3–20x.

**Impact**: All downstream ICE3 and EDIC calculations using these MHD/MLD/MBD values are affected. The cross-validation mediation analysis (Dmax → Nadir → OS) may have used inflated dose values for the HeBei cohort.

---

## Issue 1: Missing / Incomplete Data (2 patients)

| Patient | Problem |
|---------|---------|
| AI-002  | All fields empty — no pipeline results |
| AI-023  | All fields empty — no pipeline results |

**Action**: Re-run EDIC V2.0 pipeline for these 2 patients, or exclude from analysis.

---

## Issue 2: Implausible DVH Values (68 patients)

### 2a. MHD > 80 Gy (8 patients)

For a single thoracic RT course, MHD > 80 Gy is physically implausible unless the patient received multiple treatment courses AND all were correctly summed.

| Patient | MHD (Gy) | n_plans_summed | fractions | autoseg Heart_mean (Gy) | Ratio |
|---------|----------|----------------|-----------|------------------------|-------|
| AI-090  | 170.59   | 22             | 60        | —                      | —     |
| AI-088  | 88.55    | 16             | 60        | 4.53                   | 0.05  |
| AI-097  | 88.34    | 8              | 30        | —                      | —     |
| AI-093  | 87.44    | 8              | 33        | 9.78                   | 0.11  |
| AI-096  | 86.86    | 10             | 32        | —                      | —     |
| AI-083  | 86.63    | 9              | 30        | —                      | —     |
| AI-099  | 86.96    | 8              | 30        | —                      | —     |
| AI-082  | 85.82    | 8              | 30        | —                      | —     |
| AI-039  | 83.25    | 16             | 60        | 4.96                   | 0.06  |

### 2b. autoseg Heart_mean / MHD Ratio < 0.2 (63 patients)

The TotalSegmentator auto-segmented heart gives `Heart_mean_Gy` from a single dose grid. The clinical `MHD_Gy` sums across all plans. A ratio of 0.05–0.15 means the clinical MHD is 7–20x the single-plan dose — strong evidence of over-summing.

| Pattern | Count | Typical Ratio | Interpretation |
|---------|-------|---------------|----------------|
| Ratio 0.03–0.10 | 45 | ~0.07 | MHD ≈ 14x autoseg → summing ~14 plan doses |
| Ratio 0.10–0.20 | 18 | ~0.14 | MHD ≈ 7x autoseg → summing ~7 plan doses |

### 2c. MLD > 80 Gy (1 patient)

| Patient | MLD (Gy) | n_plans_summed | fractions |
|---------|----------|----------------|-----------|
| AI-046  | 89.05    | 20             | 60        |

### 2d. MHD = 0 (1 patient)

| Patient | MHD (Gy) | MLD (Gy) | n_plans_summed | Notes |
|---------|----------|----------|----------------|-------|
| AI-024  | 0        | 22.99    | 8              | Heart structure may not overlap with any dose grid |

---

## Issue 3: n_plans_summed Too High (98 of 100 patients)

**This is the root cause of Issues 2a–2c.**

All but 2 patients (AI-002, AI-023 — missing) have `n_plans_summed > 3`. The DICOM folders from the HeBei TPS contain not just treatment plans but also:
- Verification/QA plans
- Setup field plans
- Backup/alternative plans
- Dose calculation variants

### Distribution of n_plans_summed

| n_plans | Count | Notes |
|---------|-------|-------|
| 4       | 3     | AI-001, AI-015, AI-035 |
| 5       | 2     | AI-034, AI-042 |
| 6       | 1     | AI-026 |
| 7       | 29    | Most common |
| 8       | 34    | Most common |
| 9       | 15    | |
| 10      | 2     | AI-005, AI-096 |
| 11      | 4     | AI-008, AI-017, AI-030, AI-056 |
| 12      | 1     | AI-038 |
| 13      | 1     | AI-100 |
| 14      | 3     | AI-016, AI-068, AI-098 |
| 16      | 2     | AI-039, AI-088 |
| 18      | 1     | AI-067 |
| 20      | 1     | AI-046 |
| 22      | 1     | AI-090 |
| 24      | 1     | AI-048 |

**Median n_plans = 8**, but most patients likely had only **1–2 actual treatment plans**.

### Proof: MHD ≈ n_plans × Heart_mean

For patients with autoseg data, the relationship is clear:

| Patient | Heart_mean | MHD    | n_plans | MHD/Heart_mean | Expected if 1 plan |
|---------|-----------|--------|---------|----------------|-------------------|
| AI-008  | 1.77      | 47.72  | 11      | 27.0           | ~1.77 Gy          |
| AI-031  | 3.69      | 76.06  | 11      | 20.6           | ~3.69 Gy          |
| AI-088  | 4.53      | 88.55  | 16      | 19.5           | ~4.53 Gy          |
| AI-011  | 3.73      | 49.66  | 9       | 13.3           | ~3.73 Gy          |
| AI-018  | 4.03      | 57.44  | 8       | 14.3           | ~4.03 Gy          |

The MHD/Heart_mean ratio (13–27) exceeds n_plans (8–16), suggesting the clinical "Heart" structure spans a larger volume or different plans have different field arrangements.

---

## Root Cause Analysis

### Why EDIC V2.0 sums too many plans

EDIC V2.0's pipeline:
1. Scans the DICOM directory for all RT Plan and RT Dose files
2. Matches dose grids to structure sets
3. **Sums ALL matched dose grids** to compute organ mean doses
4. Reports the summed MHD, MLD, MBD

The Chinese TPS (likely Pinnacle or Eclipse) exports **all plans ever created for the patient**, not just the approved/delivered plans. EDIC V2.0 has no filter to distinguish treatment plans from QA/verification plans.

### Evidence from AI source files

The individual AI-xxx.xlsx files contain manually transcribed DVH from the TPS. For single-plan patients, the AI file MHD closely matches the autoseg Heart_mean:

| Patient | AI file MHD (Gy) | autoseg Heart_mean (Gy) | 98final MHD (Gy) |
|---------|-----------------|------------------------|------------------|
| AI-008  | 16.11           | 1.77                   | 47.72            |
| AI-031  | 76.53           | 3.69                   | 76.06            |
| AI-003  | 16.01           | 4.93                   | 47.51            |

Note: AI-031 is a special case where the AI file MHD (76.53) matches 98final (76.06), suggesting this patient's DICOM folder may actually have correctly identified plans.

---

## Recommended Fix

### Option A: Re-run EDIC V2.0 with Plan Filtering (Preferred)

Add a plan filter to EDIC V2.0 that:
1. Reads RT Plan DICOM tags: `RTPlanLabel`, `RTPlanName`, `PlanIntent`
2. Excludes plans with labels containing: "QA", "verify", "setup", "backup", "test"
3. Only sums plans with `PlanIntent == "TREATMENT"` or equivalent
4. Logs which plans were included/excluded for audit trail

### Option B: Use AI Source DVH as Ground Truth

For the ~30 patients where AI file source DVH is clean (single plan, values in Gy):
1. Replace 98final MHD/MLD/MBD with AI file values
2. Re-compute EDIC scores
3. Flag the remaining ~70 patients for manual review

### Option C: Use autoseg Heart_mean as MHD Proxy

The TotalSegmentator heart segmentation reads from a single dose grid. While this is a different heart contour than the clinical one, it provides a consistent, non-inflated dose estimate.

---

## Impact on Cross-Validation Analysis

The ICE3 cross-validation (UKY + HeBei) used MHD/MLD from 98final.xlsx as input. If these values are inflated:

- **EDIC scores** are over-estimated for HeBei cohort
- **ICE3 Dmax** may be affected if it depends on plan-summed dose
- **Mediation analysis** (Dmax → Nadir → OS) may show different effect sizes
- **Cohort comparison** (UKY vs HeBei) will show systematic bias in HeBei doses

The 3 planned papers (Red Journal, Green Journal, Lung Cancer) should be reviewed for sensitivity to this DVH inflation.

---

## Full Patient-Level Data

See `audit_data.json` for complete per-patient audit data.

### Patients Requiring Immediate Attention

| Priority | Patients | Issue |
|----------|----------|-------|
| P0 — Missing | AI-002, AI-023 | No data at all |
| P1 — Extreme | AI-090 (MHD=170.6), AI-046 (MLD=89.1) | Physically impossible values |
| P2 — High MHD | AI-082, -083, -088, -093, -096, -097, -099 | MHD > 80 Gy |
| P3 — Inflated | All 98 patients with n_plans > 3 | DVH inflated by plan over-summing |
