"""SCART HCC Analysis V3 — Updated data (03/11/2026) with AICE3 integration.

Reads the updated SCART Excel + AICE3 CSV, reproduces V2 report analyses,
and compares key metrics against the previous V2 report.

Usage:
    python scripts/analyze_scart_v3.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test
from scipy import stats

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────
NEW_DATA_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OLD_REPORT = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Analysis V2/SCART_Analysis_Report_V2.xlsx")
OUTPUT_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OUTPUT_XLSX = OUTPUT_DIR / "SCART_Analysis_Report_V3.xlsx"

# ── column aliases (long Chinese names → short keys) ──────────────────────
COL = {
    "case_id": "数据定位编号（患者-肿瘤-疗程）",
    "patient_id": "ID",
    "name": "中文名",
    "dob": "出生日期",
    "center": "中心",
    "age": "Age (年龄）",
    "sex": "Sex （性别）",
    "histology": "Tumor Histology (组织病理诊断）",
    "cnlc": "CNLC Stage",
    "bclc": "BCLC Stage",
    "gtv": "GTV size (肿瘤大小 体积）volume  in cm3",
    "total_dose": "Total Dose (剂量）Gy*f",
    "bed": "BED",
    "eqd2": "EQD2",
    "scart_dose": "SCART Dose(剂量)",
    "scart_fx": "SCART  F",
    "stv": "STV size (V prescription) volume  in cm3",
    "os_event": "生存情况（1，0）",
    "os_months_dx": "生存时间（month）=（死亡日期-诊断日期）/30",
    "os_months_rt": "Post-SCART survival days（放疗后存活时长）",
    "immuno_yn": "围放疗期免疫（前1m后3m)Y or N",
    "targeted_yn": "围放疗期靶向（前1m后3m)Y or N",
    "interv_yn": "围放疗期介入（前1m后3m)Y or N",
    "chemo_yn": "围放疗期系统化疗（前1m后3m)Y or N",
    "cp_pre": "治疗前CP评分",
    "cp_post": "治疗后1月CP评分",
    "tox": "Radiation Toxicity （毒性）要用 Grade 1,2,3 来记录",
    "response_local": "Response Local（肿瘤局部 反应）Based on RECIST criteria, response to treatment was defined as a 30% or greater regression o",
    "scart_start": "SCART治疗日期",
    "scart_end": "末次SCART日期",
    "death_date": "死亡日期",
    "last_fu": "末次随访日期",
}


# ═══════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_survival_data() -> pd.DataFrame:
    """Load and clean the 生存数据 sheet."""
    df = pd.read_excel(NEW_DATA_DIR / "SCART 03092026.xlsx", sheet_name="生存数据")
    df.columns = [str(c).strip() for c in df.columns]

    # Rename to short keys where possible
    inv_col = {v: k for k, v in COL.items() if v in df.columns}
    df = df.rename(columns=inv_col)

    # Numeric coercion
    for c in ["age", "gtv", "total_dose", "bed", "eqd2", "scart_dose", "scart_fx",
              "os_event", "os_months_dx", "os_months_rt",
              "immuno_yn", "targeted_yn", "interv_yn", "chemo_yn"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Derive immuno_group
    df["immuno_group"] = df["immuno_yn"].apply(
        lambda x: "SCART+Immunotherapy" if x == 1 else "SCART Alone"
    )

    # Flip event coding: source 生存情况 1=alive 0=dead → KM convention 1=event(death)
    df["os_event"] = 1 - df["os_event"]

    # Parse date columns for per-course OS calculation (matches V2 formula)
    for dcol in ["scart_start", "scart_end", "death_date", "last_fu"]:
        if dcol in df.columns:
            df[dcol] = pd.to_datetime(df[dcol], errors="coerce")

    # V2 OS formula: endpoint = death_date if present, else last_fu; then (endpoint - scart_start) / 30.44
    endpoint = df["death_date"].where(df["death_date"].notna(), df["last_fu"])
    df["os_months"] = (endpoint - df["scart_start"]).dt.days / 30.44

    # Data correction: if death_date is present, patient died → os_event must be 1
    df.loc[df["death_date"].notna(), "os_event"] = 1

    # Parse tox grade
    df["tox_grade"] = df["tox"].apply(_parse_tox_grade)

    # GTV grouping
    median_gtv = df["gtv"].median()
    df["gtv_group"] = df["gtv"].apply(
        lambda x: f"GTV > {median_gtv:.0f} cm3" if x > median_gtv else f"GTV <= {median_gtv:.0f} cm3"
    )

    return df


def _parse_tox_grade(val) -> int:
    """Extract maximum toxicity grade from Chinese text."""
    if pd.isna(val) or str(val).strip() == "":
        return 0
    text = str(val)
    grades = []
    for g in ["1", "2", "3", "4", "5"]:
        if f"{g}级" in text or f"grade {g}" in text.lower() or f"Grade {g}" in text:
            grades.append(int(g))
    return max(grades) if grades else 0


def load_oar_data() -> pd.DataFrame:
    """Load OAR dose sheet."""
    df = pd.read_excel(NEW_DATA_DIR / "SCART 03092026.xlsx", sheet_name="OAR", header=None)
    # Row 0 is version/organ headers, row 1 is metric sub-headers
    # Build proper column names
    organ_row = df.iloc[0].ffill()
    metric_row = df.iloc[1]
    columns = []
    for i in range(len(organ_row)):
        org = str(organ_row.iloc[i]).strip() if pd.notna(organ_row.iloc[i]) else ""
        met = str(metric_row.iloc[i]).strip() if pd.notna(metric_row.iloc[i]) else ""
        if org.startswith("版本"):
            columns.append(met if met and met != "nan" else f"col_{i}")
        elif met and met != "nan":
            columns.append(f"{org}_{met}")
        else:
            columns.append(org if org else f"col_{i}")
    df.columns = columns
    df = df.iloc[2:].reset_index(drop=True)

    # Rename ID columns
    rename_map = {}
    for c in df.columns:
        if c in ("col_0", "版本：260309"):
            rename_map[c] = "case_id"
        elif c == "ID":
            rename_map[c] = "patient_id"
    df = df.rename(columns=rename_map)

    # Numeric coercion for dose columns
    dose_cols = [c for c in df.columns if "_D" in c or "Dmax" in c or "D5cc" in c or "D30cc" in c or "D20cc" in c or "D700cc" in c]
    for c in dose_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def load_imaging_data() -> pd.DataFrame:
    """Load imaging/tumor size sheet."""
    df = pd.read_excel(NEW_DATA_DIR / "SCART 03092026.xlsx", sheet_name="影像及肿瘤尺寸", header=None)
    header_row = df.iloc[0]
    columns = []
    for i, val in enumerate(header_row):
        s = str(val).strip() if pd.notna(val) else f"col_{i}"
        if s.startswith("版本"):
            s = "case_id"
        columns.append(s)
    df.columns = columns
    df = df.iloc[1:].reset_index(drop=True)
    return df


def load_aice3() -> pd.DataFrame:
    """Load AICE3 immune-dose results."""
    return pd.read_csv(NEW_DATA_DIR / "liver_cases_aice3_results.csv")


def load_old_report() -> dict[str, pd.DataFrame]:
    """Load all sheets from the V2 report for comparison."""
    xls = pd.ExcelFile(OLD_REPORT)
    return {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def baseline_characteristics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute baseline characteristics by immuno group."""
    groups = {"SCART+Immunotherapy": df[df["immuno_group"] == "SCART+Immunotherapy"],
              "SCART Alone": df[df["immuno_group"] == "SCART Alone"]}
    rows = []

    # N
    rows.append({"Characteristic": "N",
                 "SCART+Immunotherapy": str(len(groups["SCART+Immunotherapy"])),
                 "SCART Alone": str(len(groups["SCART Alone"])),
                 "p-value": ""})

    # Continuous variables
    for label, col in [("Age, median [IQR]", "age"), ("GTV (cm3), median [IQR]", "gtv"),
                       ("Total Dose (Gy), median [IQR]", "total_dose"),
                       ("BED, median [IQR]", "bed"), ("EQD2, median [IQR]", "eqd2")]:
        vals = {}
        for gname, gdf in groups.items():
            v = gdf[col].dropna()
            if len(v) > 0:
                q1, med, q3 = v.quantile([0.25, 0.5, 0.75])
                vals[gname] = f"{med:.1f} [{q1:.1f}-{q3:.1f}]"
            else:
                vals[gname] = "N/A"
        # Mann-Whitney test
        a = groups["SCART+Immunotherapy"][col].dropna()
        b = groups["SCART Alone"][col].dropna()
        if len(a) > 1 and len(b) > 1:
            _, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            pval = f"{p:.3f}"
        else:
            pval = "N/A"
        rows.append({"Characteristic": label, **vals, "p-value": pval})

    # Categorical variables
    for label, col, categories in [
        ("Sex (Male)", "sex", ["男"]),
        ("BCLC A", "bclc", ["A"]),
        ("BCLC B", "bclc", ["B"]),
        ("BCLC C", "bclc", ["C"]),
        ("Targeted therapy", "targeted_yn", [1.0]),
        ("Intervention (TACE)", "interv_yn", [1.0]),
        ("Chemotherapy", "chemo_yn", [1.0]),
    ]:
        vals = {}
        for gname, gdf in groups.items():
            total = len(gdf)
            count = gdf[col].isin(categories).sum()
            vals[gname] = f"{count} ({count/total*100:.0f}%)" if total > 0 else "N/A"
        # Fisher exact for 2x2
        a_yes = groups["SCART+Immunotherapy"][col].isin(categories).sum()
        a_no = len(groups["SCART+Immunotherapy"]) - a_yes
        b_yes = groups["SCART Alone"][col].isin(categories).sum()
        b_no = len(groups["SCART Alone"]) - b_yes
        if a_yes + a_no > 0 and b_yes + b_no > 0:
            _, p = stats.fisher_exact([[a_yes, a_no], [b_yes, b_no]])
            pval = f"{p:.3f}"
        else:
            pval = "N/A"
        rows.append({"Characteristic": label, **vals, "p-value": pval})

    return pd.DataFrame(rows)


def km_analysis(df: pd.DataFrame, group_col: str, time_col: str = "os_months",
                event_col: str = "os_event") -> pd.DataFrame:
    """Kaplan-Meier analysis by group."""
    valid = df.dropna(subset=[time_col, event_col, group_col])
    valid = valid[valid[time_col] > 0]
    groups = sorted(valid[group_col].unique())
    results = []

    for g in groups:
        mask = valid[group_col] == g
        T = valid.loc[mask, time_col]
        E = valid.loc[mask, event_col].astype(int)
        kmf = KaplanMeierFitter()
        kmf.fit(T, E)
        median_surv = kmf.median_survival_time_
        ci = kmf.confidence_interval_survival_function_
        results.append({
            "Group": g,
            "N": int(mask.sum()),
            "Events": int(E.sum()),
            "Median_OS_months": round(median_surv, 2) if np.isfinite(median_surv) else "NR",
            "1yr_survival": f"{kmf.predict(12)*100:.1f}%" if T.max() >= 12 else "N/A",
            "2yr_survival": f"{kmf.predict(24)*100:.1f}%" if T.max() >= 24 else "N/A",
        })

    # Log-rank test (pairwise if 2 groups, overall if more)
    if len(groups) == 2:
        g1 = valid[valid[group_col] == groups[0]]
        g2 = valid[valid[group_col] == groups[1]]
        lr = logrank_test(
            g1[time_col], g2[time_col],
            g1[event_col].astype(int), g2[event_col].astype(int)
        )
        for r in results:
            r["Log_rank_p"] = round(lr.p_value, 4)
    elif len(groups) > 2:
        # Multi-group log-rank
        from lifelines.statistics import multivariate_logrank_test
        lr = multivariate_logrank_test(valid[time_col], valid[group_col], valid[event_col].astype(int))
        for r in results:
            r["Log_rank_p"] = round(lr.p_value, 4)

    return pd.DataFrame(results)


def cox_regression(df: pd.DataFrame) -> pd.DataFrame:
    """Multivariable Cox proportional hazards."""
    covariates = ["immuno_yn", "age", "gtv"]
    valid = df.dropna(subset=["os_months", "os_event"] + covariates)
    valid = valid[valid["os_months"] > 0].copy()

    results_list = []

    # Model 1: Unadjusted
    for cov in covariates:
        cph = CoxPHFitter()
        cph.fit(valid[["os_months", "os_event", cov]], duration_col="os_months", event_col="os_event")
        s = cph.summary.loc[cov]
        results_list.append({
            "Model": "Univariable",
            "Covariate": cov,
            "HR": round(s["exp(coef)"], 4),
            "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
            "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
            "p": round(s["p"], 4),
        })

    # Model 2: Adjusted
    cph = CoxPHFitter()
    cph.fit(valid[["os_months", "os_event"] + covariates], duration_col="os_months", event_col="os_event")
    for cov in covariates:
        s = cph.summary.loc[cov]
        results_list.append({
            "Model": "Adjusted (age+GTV+immuno)",
            "Covariate": cov,
            "HR": round(s["exp(coef)"], 4),
            "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
            "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
            "p": round(s["p"], 4),
        })

    # Model 3: With CNLC stage (ordinal)
    cnlc_map = {"Ia": 1, "Ib": 2, "IIa": 3, "IIb": 4, "IIIa": 5, "IIIb": 6, "IV": 7}
    valid2 = valid.copy()
    valid2["cnlc_ord"] = valid2["cnlc"].map(cnlc_map)
    valid2 = valid2.dropna(subset=["cnlc_ord"])
    if len(valid2) > 10:
        cph2 = CoxPHFitter()
        covs2 = covariates + ["cnlc_ord"]
        cph2.fit(valid2[["os_months", "os_event"] + covs2], duration_col="os_months", event_col="os_event")
        for cov in covs2:
            s = cph2.summary.loc[cov]
            results_list.append({
                "Model": "Adjusted (age+GTV+immuno+CNLC)",
                "Covariate": cov,
                "HR": round(s["exp(coef)"], 4),
                "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
                "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
                "p": round(s["p"], 4),
            })

    return pd.DataFrame(results_list)


def oar_summary(oar_df: pd.DataFrame, surv_df: pd.DataFrame) -> pd.DataFrame:
    """OAR dose summary with constraint compliance."""
    # Merge immuno status
    id_to_immuno = dict(zip(surv_df["case_id"].astype(str), surv_df["immuno_group"]))
    oar_df["immuno_group"] = oar_df["case_id"].astype(str).map(id_to_immuno)

    constraints = {
        "SInte_Dmax": ("Small Intestine Dmax (Gy)", 21.0),
        "SInte_D30cc": ("Small Intestine D30cc (Gy)", None),
        "Duode_Dmax": ("Duodenum Dmax (Gy)", 21.0),
        "Duode_D5cc": ("Duodenum D5cc (Gy)", None),
        "Colon_Dmax": ("Colon Dmax (Gy)", 30.0),
        "Colon_D20cc": ("Colon D20cc (Gy)", None),
        "Stom_Dmax": ("Stomach Dmax (Gy)", 21.0),
        "Stom_D5cc": ("Stomach D5cc (Gy)", None),
        "Liv-GTV_Dmax": ("Liver-GTV Dmax (Gy)", None),
        "Liv-GTV_D700cc": ("Liver-GTV D700cc (Gy)", 15.0),
        "Spleen_Dmax": ("Spleen Dmax (Gy)", None),
    }

    rows = []
    for col_key, (label, limit) in constraints.items():
        # Find matching column
        matching = [c for c in oar_df.columns if col_key in c.replace(" ", "")]
        if not matching:
            # Try looser match
            matching = [c for c in oar_df.columns if col_key.replace("-", "") in c.replace("-", "").replace(" ", "")]
        if not matching:
            continue
        col = matching[0]
        vals = pd.to_numeric(oar_df[col], errors="coerce").dropna()
        if vals.empty:
            continue

        exceed = f"{(vals > limit).sum()} ({(vals > limit).mean()*100:.0f}%)" if limit else "N/A"

        # Mann-Whitney by immuno group
        io_vals = pd.to_numeric(oar_df.loc[oar_df["immuno_group"] == "SCART+Immunotherapy", col], errors="coerce").dropna()
        alone_vals = pd.to_numeric(oar_df.loc[oar_df["immuno_group"] == "SCART Alone", col], errors="coerce").dropna()
        if len(io_vals) > 1 and len(alone_vals) > 1:
            _, mw_p = stats.mannwhitneyu(io_vals, alone_vals, alternative="two-sided")
            mw_str = f"{mw_p:.3f}"
        else:
            mw_str = "N/A"

        rows.append({
            "OAR Metric": label,
            "N": int(len(vals)),
            "Median": round(vals.median(), 2),
            "Range": f"{vals.min():.2f}-{vals.max():.2f}",
            "Mean +/- SD": f"{vals.mean():.2f} +/- {vals.std():.2f}",
            "Constraint": f"<= {limit} Gy" if limit else "",
            "Exceed": exceed,
            "MW p (IO vs Alone)": mw_str,
        })

    return pd.DataFrame(rows)


def toxicity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Toxicity distribution by group."""
    rows = []
    for gname in ["SCART+Immunotherapy", "SCART Alone"]:
        gdf = df[df["immuno_group"] == gname]
        n = len(gdf)
        if n == 0:
            continue
        grade_counts = gdf["tox_grade"].value_counts()
        row = {"Group": gname, "N": n}
        for g in range(5):
            cnt = grade_counts.get(g, 0)
            row[f"Grade {g}"] = f"{cnt} ({cnt/n*100:.0f}%)"
        ge2 = gdf[gdf["tox_grade"] >= 2].shape[0]
        row["Grade >=2"] = f"{ge2} ({ge2/n*100:.0f}%)"
        rows.append(row)
    return pd.DataFrame(rows)


def imaging_response(img_df: pd.DataFrame, surv_df: pd.DataFrame) -> pd.DataFrame:
    """Compute imaging-based response from tumor size timepoints."""
    # Map case_id → immuno_group
    id_to_immuno = dict(zip(surv_df["case_id"].astype(str), surv_df["immuno_group"]))

    records = []
    for _, row in img_df.iterrows():
        case_id = str(row.get("case_id", ""))
        name = row.get("中文名", "")
        immuno = id_to_immuno.get(case_id, "Unknown")

        # Collect size measurements
        sizes = []
        baseline = None
        for i in range(1, 21):
            size_col = f"尺寸{i:02d}"
            if size_col in img_df.columns:
                val = pd.to_numeric(row.get(size_col), errors="coerce")
                if pd.notna(val) and val > 0:
                    if baseline is None:
                        baseline = val
                    sizes.append(val)

        if baseline is None or len(sizes) < 2:
            continue

        best = min(sizes[1:])
        last = sizes[-1]
        pct_best = (best - baseline) / baseline * 100
        pct_last = (last - baseline) / baseline * 100

        # RECIST-like classification
        if pct_best <= -100:
            response = "CR"
        elif pct_best <= -30:
            response = "PR"
        elif pct_last >= 20:
            response = "PD"
        else:
            response = "SD"

        records.append({
            "case_id": case_id,
            "name": name,
            "immuno_group": immuno,
            "response": response,
            "pct_change_best": round(pct_best, 1),
            "pct_change_last": round(pct_last, 1),
            "baseline_size": baseline,
            "last_size": last,
            "n_timepoints": len(sizes),
        })

    resp_df = pd.DataFrame(records)

    # Summarize by group
    summary_rows = []
    for gname in ["SCART+Immunotherapy", "SCART Alone"]:
        gdf = resp_df[resp_df["immuno_group"] == gname]
        n = len(gdf)
        if n == 0:
            summary_rows.append({"Group": gname, "N": 0})
            continue
        rc = gdf["response"].value_counts()
        row = {"Group": gname, "N": n}
        for r in ["CR", "PR", "SD", "PD"]:
            cnt = rc.get(r, 0)
            row[r] = f"{cnt} ({cnt/n*100:.0f}%)"
        orr = rc.get("CR", 0) + rc.get("PR", 0)
        dcr = orr + rc.get("SD", 0)
        row["ORR"] = f"{orr} ({orr/n*100:.0f}%)"
        row["DCR"] = f"{dcr} ({dcr/n*100:.0f}%)"
        summary_rows.append(row)

    return pd.DataFrame(summary_rows), resp_df


def aice3_analysis(surv_df: pd.DataFrame, aice_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze AICE3 dose-to-immune-cells metrics and their prognostic value."""
    # Merge
    merged = surv_df.merge(aice_df, left_on="case_id", right_on="case_id", how="inner",
                           suffixes=("", "_aice"))

    # Descriptive stats by immuno group
    aice_cols = ["H_mean_blood_gy", "H_body_dyn_gy", "H_liver_dyn_gy", "H_spleen_dyn_gy",
                 "E_dyn", "E_static", "AICE3_raw", "damage_proxy",
                 "mean_liver_gy_per_fx", "mean_spleen_gy_per_fx", "mean_body_gy_per_fx"]

    desc_rows = []
    for col in aice_cols:
        if col not in merged.columns:
            continue
        for gname in ["SCART+Immunotherapy", "SCART Alone", "All"]:
            if gname == "All":
                vals = pd.to_numeric(merged[col], errors="coerce").dropna()
            else:
                vals = pd.to_numeric(merged.loc[merged["immuno_group"] == gname, col], errors="coerce").dropna()
            if vals.empty:
                continue
            desc_rows.append({
                "Metric": col,
                "Group": gname,
                "N": len(vals),
                "Median": round(vals.median(), 4),
                "IQR": f"[{vals.quantile(0.25):.4f}-{vals.quantile(0.75):.4f}]",
                "Mean_SD": f"{vals.mean():.4f} +/- {vals.std():.4f}",
                "Range": f"{vals.min():.4f}-{vals.max():.4f}",
            })

    desc_df = pd.DataFrame(desc_rows)

    # Mann-Whitney comparison IO vs Alone
    mw_rows = []
    for col in aice_cols:
        if col not in merged.columns:
            continue
        io = pd.to_numeric(merged.loc[merged["immuno_group"] == "SCART+Immunotherapy", col], errors="coerce").dropna()
        alone = pd.to_numeric(merged.loc[merged["immuno_group"] == "SCART Alone", col], errors="coerce").dropna()
        if len(io) > 1 and len(alone) > 1:
            stat, p = stats.mannwhitneyu(io, alone, alternative="two-sided")
            mw_rows.append({
                "Metric": col,
                "N_IO": len(io),
                "Median_IO": round(io.median(), 4),
                "N_Alone": len(alone),
                "Median_Alone": round(alone.median(), 4),
                "U_statistic": round(stat, 2),
                "p_value": round(p, 4),
            })

    # Prognostic Cox models for key AICE3 metrics
    cox_rows = []
    for col in ["AICE3_raw", "damage_proxy", "H_mean_blood_gy", "E_dyn"]:
        if col not in merged.columns:
            continue
        subset = merged.dropna(subset=["os_months", "os_event", col])
        subset = subset[subset["os_months"] > 0].copy()
        if len(subset) < 10:
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(subset[[col, "os_months", "os_event"]], duration_col="os_months", event_col="os_event")
            s = cph.summary.loc[col]
            cox_rows.append({
                "AICE3_Metric": col,
                "HR": round(s["exp(coef)"], 4),
                "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
                "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
                "p": round(s["p"], 4),
                "concordance": round(cph.concordance_index_, 4),
            })
        except Exception:
            pass

    mw_df = pd.DataFrame(mw_rows)
    cox_df = pd.DataFrame(cox_rows)

    return desc_df, mw_df, cox_df


def bclc_subgroup_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """OS by BCLC stage with IO vs Alone."""
    rows = []
    for bclc in sorted(df["bclc"].dropna().unique()):
        sub = df[df["bclc"] == bclc]
        valid = sub.dropna(subset=["os_months", "os_event"])
        valid = valid[valid["os_months"] > 0]
        if len(valid) < 2:
            continue

        n_io = (valid["immuno_group"] == "SCART+Immunotherapy").sum()
        n_alone = (valid["immuno_group"] == "SCART Alone").sum()

        # Overall KM
        kmf = KaplanMeierFitter()
        kmf.fit(valid["os_months"], valid["os_event"].astype(int))
        mos = kmf.median_survival_time_
        yr1 = f"{kmf.predict(12)*100:.0f}%" if valid["os_months"].max() >= 12 else "N/A"

        # By immuno group
        mos_io = "N/A"
        mos_alone = "N/A"
        yr1_io = "N/A"
        yr1_alone = "N/A"
        dr_io = "N/A"
        dr_alone = "N/A"

        for gname, prefix in [("SCART+Immunotherapy", "io"), ("SCART Alone", "alone")]:
            gdf = valid[valid["immuno_group"] == gname]
            if len(gdf) >= 2:
                kmf_g = KaplanMeierFitter()
                kmf_g.fit(gdf["os_months"], gdf["os_event"].astype(int))
                m = kmf_g.median_survival_time_
                if prefix == "io":
                    mos_io = f"{m:.1f}" if np.isfinite(m) else "NR"
                    yr1_io = f"{kmf_g.predict(12)*100:.0f}%" if gdf["os_months"].max() >= 12 else "N/A"
                    dr_io = f"{gdf['os_event'].sum()}/{len(gdf)} ({gdf['os_event'].mean()*100:.0f}%)"
                else:
                    mos_alone = f"{m:.1f}" if np.isfinite(m) else "NR"
                    yr1_alone = f"{kmf_g.predict(12)*100:.0f}%" if gdf["os_months"].max() >= 12 else "N/A"
                    dr_alone = f"{int(gdf['os_event'].sum())}/{len(gdf)} ({gdf['os_event'].mean()*100:.0f}%)"

        rows.append({
            "BCLC": bclc,
            "N_total": len(valid),
            "N_IO": n_io,
            "N_Alone": n_alone,
            "mOS_All": f"{mos:.1f}" if np.isfinite(mos) else "NR",
            "mOS_IO": mos_io,
            "mOS_Alone": mos_alone,
            "1yr_All": yr1,
            "1yr_IO": yr1_io,
            "1yr_Alone": yr1_alone,
            "DeathRate_IO": dr_io,
            "DeathRate_Alone": dr_alone,
        })

    return pd.DataFrame(rows)


def patient_summary(surv_df: pd.DataFrame, aice_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build clean patient-level summary table."""
    cols = ["case_id", "patient_id", "name", "age", "sex", "center",
            "cnlc", "bclc", "immuno_group", "targeted_yn", "interv_yn", "chemo_yn",
            "gtv", "total_dose", "bed", "eqd2", "scart_dose", "scart_fx",
            "response_local", "tox_grade", "os_months", "os_event",
            "cp_pre", "cp_post"]
    out = surv_df[[c for c in cols if c in surv_df.columns]].copy()

    if aice_df is not None:
        # Merge key AICE3 columns
        aice_merge_cols = ["case_id", "AICE3_raw", "damage_proxy", "H_mean_blood_gy", "E_dyn", "E_static"]
        aice_merge_cols = [c for c in aice_merge_cols if c in aice_df.columns]
        out = out.merge(aice_df[aice_merge_cols], on="case_id", how="left")

    return out


# ═══════════════════════════════════════════════════════════════════════════
#  COMPARISON
# ═══════════════════════════════════════════════════════════════════════════

def compare_reports(new_results: dict, old_sheets: dict) -> pd.DataFrame:
    """Compare key metrics between V2 and V3."""
    comparisons = []

    # Patient counts
    old_ps = old_sheets.get("Patient_Summary")
    if old_ps is not None:
        comparisons.append({"Metric": "Total cases (Patient_Summary rows)",
                            "V2": len(old_ps) - 1,  # header row already excluded by read_excel
                            "V3": len(new_results["Patient_Summary"]),
                            "Change": ""})

    # OS by immuno group
    old_os = old_sheets.get("OS_KM_Results")
    new_os = new_results.get("OS_by_Immuno")
    if old_os is not None and new_os is not None:
        for group in ["SCART Alone", "SCART+Immunotherapy"]:
            old_row = old_os[old_os["Group"] == group]
            new_row = new_os[new_os["Group"] == group]
            if len(old_row) > 0 and len(new_row) > 0:
                old_n = old_row["N"].iloc[0]
                new_n = new_row["N"].iloc[0]
                old_med = old_row["Median"].iloc[0]
                new_med = new_row["Median_OS_months"].iloc[0]
                old_events = old_row["Events"].iloc[0]
                new_events = new_row["Events"].iloc[0]
                comparisons.append({"Metric": f"{group} — N",
                                    "V2": old_n, "V3": new_n,
                                    "Change": f"{new_n - old_n:+d}" if isinstance(new_n, (int, np.integer)) else ""})
                comparisons.append({"Metric": f"{group} — Events",
                                    "V2": old_events, "V3": new_events,
                                    "Change": f"{new_events - old_events:+d}" if isinstance(new_events, (int, np.integer)) else ""})
                comparisons.append({"Metric": f"{group} — Median OS (months)",
                                    "V2": old_med, "V3": new_med, "Change": ""})

        # Log-rank p
        if len(old_os) > 0 and len(new_os) > 0:
            old_p = old_os["Log_rank_p"].iloc[0]
            new_p = new_os["Log_rank_p"].iloc[0] if "Log_rank_p" in new_os.columns else "N/A"
            comparisons.append({"Metric": "Log-rank p (IO vs Alone)",
                                "V2": round(old_p, 4) if pd.notna(old_p) else "N/A",
                                "V3": new_p, "Change": ""})

    # Baseline characteristics comparison
    old_bl = old_sheets.get("Baseline_Characteristics")
    new_bl = new_results.get("Baseline_Characteristics")
    if old_bl is not None and new_bl is not None:
        for _, old_r in old_bl.iterrows():
            char = old_r.get("Characteristic", "")
            new_match = new_bl[new_bl["Characteristic"] == char]
            if len(new_match) > 0:
                comparisons.append({
                    "Metric": f"Baseline: {char}",
                    "V2": f"IO={old_r.get('SCART+Immunotherapy', '')} | Alone={old_r.get('SCART Alone', '')}",
                    "V3": f"IO={new_match['SCART+Immunotherapy'].iloc[0]} | Alone={new_match['SCART Alone'].iloc[0]}",
                    "Change": "",
                })

    # BCLC subgroup OS
    old_bclc = old_sheets.get("OS_by_BCLC")
    new_bclc = new_results.get("OS_by_BCLC")
    if old_bclc is not None and new_bclc is not None:
        for _, old_r in old_bclc.iterrows():
            g = old_r.get("Group", "")
            new_match = new_bclc[new_bclc["Group"] == g]
            if len(new_match) > 0:
                comparisons.append({
                    "Metric": f"BCLC {g} — Median OS",
                    "V2": old_r.get("Median", ""),
                    "V3": new_match["Median_OS_months"].iloc[0],
                    "Change": "",
                })

    # Imaging response
    old_img = old_sheets.get("Imaging_Response")
    new_img = new_results.get("Imaging_Response_Summary")
    if old_img is not None and new_img is not None:
        for group in ["SCART+Immunotherapy", "SCART Alone"]:
            old_row = old_img[old_img["Group"] == group]
            new_row = new_img[new_img["Group"] == group]
            if len(old_row) > 0 and len(new_row) > 0:
                comparisons.append({
                    "Metric": f"Imaging ORR — {group}",
                    "V2": old_row["ORR"].iloc[0],
                    "V3": new_row.get("ORR", pd.Series(["N/A"])).iloc[0],
                    "Change": "",
                })

    # New: AICE3 metrics (no V2 comparison)
    aice_desc = new_results.get("AICE3_Descriptive")
    if aice_desc is not None and len(aice_desc) > 0:
        for metric in ["AICE3_raw", "damage_proxy", "H_mean_blood_gy"]:
            all_row = aice_desc[(aice_desc["Metric"] == metric) & (aice_desc["Group"] == "All")]
            if len(all_row) > 0:
                comparisons.append({
                    "Metric": f"AICE3 {metric} (All, median)",
                    "V2": "N/A (new metric)",
                    "V3": all_row["Median"].iloc[0],
                    "Change": "NEW",
                })

    return pd.DataFrame(comparisons)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("Loading data...")
    surv_df = load_survival_data()
    oar_df = load_oar_data()
    img_df = load_imaging_data()
    aice_df = load_aice3()
    old_sheets = load_old_report()

    print(f"  Survival data: {len(surv_df)} cases")
    print(f"  OAR data: {len(oar_df)} cases")
    print(f"  Imaging data: {len(img_df)} cases")
    print(f"  AICE3 data: {len(aice_df)} cases")
    print(f"  Old V2 report: {len(old_sheets)} sheets")

    results: dict[str, pd.DataFrame] = {}

    # 1. Patient Summary
    print("\n1. Building Patient Summary...")
    results["Patient_Summary"] = patient_summary(surv_df, aice_df)
    print(f"   → {len(results['Patient_Summary'])} rows")

    # 2. Baseline Characteristics
    print("2. Baseline Characteristics...")
    results["Baseline_Characteristics"] = baseline_characteristics(surv_df)
    print(f"   → {len(results['Baseline_Characteristics'])} rows")

    # 3. OS by Immunotherapy group
    print("3. OS Kaplan-Meier (IO vs Alone)...")
    results["OS_by_Immuno"] = km_analysis(surv_df, "immuno_group")
    for _, r in results["OS_by_Immuno"].iterrows():
        print(f"   {r['Group']}: N={r['N']}, Events={r['Events']}, mOS={r['Median_OS_months']}")

    # 4. OS by BCLC stage
    print("4. OS by BCLC stage...")
    results["OS_by_BCLC"] = km_analysis(surv_df, "bclc")
    for _, r in results["OS_by_BCLC"].iterrows():
        print(f"   BCLC {r['Group']}: N={r['N']}, mOS={r['Median_OS_months']}")

    # 5. OS by GTV
    print("5. OS by GTV group...")
    results["OS_by_GTV"] = km_analysis(surv_df, "gtv_group")
    for _, r in results["OS_by_GTV"].iterrows():
        print(f"   {r['Group']}: N={r['N']}, mOS={r['Median_OS_months']}")

    # 6. Cox Regression
    print("6. Cox Regression...")
    results["Cox_Regression"] = cox_regression(surv_df)
    print(f"   → {len(results['Cox_Regression'])} rows")

    # 7. OAR Dose Summary
    print("7. OAR Dose Summary...")
    results["OAR_Dose_Summary"] = oar_summary(oar_df, surv_df)
    print(f"   → {len(results['OAR_Dose_Summary'])} rows")

    # 8. Toxicity Summary
    print("8. Toxicity Summary...")
    results["Toxicity_Summary"] = toxicity_summary(surv_df)
    print(f"   → {len(results['Toxicity_Summary'])} rows")

    # 9. Imaging Response
    print("9. Imaging Response...")
    img_summary, img_raw = imaging_response(img_df, surv_df)
    results["Imaging_Response_Summary"] = img_summary
    results["Imaging_Response_Raw"] = img_raw
    print(f"   Summary: {len(img_summary)} groups, Raw: {len(img_raw)} cases")

    # 10. BCLC Subgroup Detail
    print("10. BCLC Subgroup Analysis...")
    results["BCLC_Subgroup_Detail"] = bclc_subgroup_analysis(surv_df)
    print(f"   → {len(results['BCLC_Subgroup_Detail'])} subgroups")

    # 11. AICE3 Analysis (NEW)
    print("11. AICE3 Immune Dose Analysis (NEW)...")
    aice_desc, aice_mw, aice_cox = aice3_analysis(surv_df, aice_df)
    results["AICE3_Descriptive"] = aice_desc
    results["AICE3_IO_vs_Alone"] = aice_mw
    results["AICE3_Cox_Prognostic"] = aice_cox
    print(f"   Descriptive: {len(aice_desc)} rows")
    print(f"   MW tests: {len(aice_mw)} metrics")
    print(f"   Cox prognostic: {len(aice_cox)} models")

    # 12. V2 vs V3 Comparison
    print("12. V2 vs V3 Comparison...")
    results["V2_vs_V3_Comparison"] = compare_reports(results, old_sheets)
    print(f"   → {len(results['V2_vs_V3_Comparison'])} comparison rows")

    # Write output
    print(f"\nWriting {OUTPUT_XLSX}...")
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        for sheet_name, df in results.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    print(f"Done! {len(results)} sheets written to:\n  {OUTPUT_XLSX}")

    # Print key comparison highlights
    comp = results["V2_vs_V3_Comparison"]
    print("\n" + "=" * 70)
    print("KEY V2 → V3 CHANGES")
    print("=" * 70)
    for _, row in comp.iterrows():
        change_str = f" [{row['Change']}]" if row["Change"] else ""
        print(f"  {row['Metric']}:")
        print(f"    V2: {row['V2']}")
        print(f"    V3: {row['V3']}{change_str}")


if __name__ == "__main__":
    main()
