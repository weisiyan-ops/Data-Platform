"""SCART V3 Matched & Adjusted Analysis — PSM, IPTW, Stratified Cox, Subgroups.

Replicates V2's PSM_Balance and Stratified_Cox sheets, plus adds IPTW and
refined subgroup analyses. Generates matched KM figures.

Usage:
    python scripts/analyze_scart_v3_matched.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.plotting import add_at_risk_counts
from lifelines.statistics import logrank_test
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OLD_REPORT = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Analysis V2/SCART_Analysis_Report_V2.xlsx")
OUTPUT_DIR = DATA_DIR
OUTPUT_XLSX = OUTPUT_DIR / "SCART_V3_Matched_Analysis.xlsx"

# ── style ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 11,
    "axes.titlesize": 13, "axes.labelsize": 12, "legend.fontsize": 10,
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.grid": False,
})
COLOR_IO = "#E63946"
COLOR_ALONE = "#457B9D"


# ═══════════════════════════════════════════════════════════════════════════
#  DATA LOADING (same as analyze_scart_v3.py)
# ═══════════════════════════════════════════════════════════════════════════

COL = {
    "case_id": "数据定位编号（患者-肿瘤-疗程）",
    "patient_id": "ID",
    "name": "中文名",
    "age": "Age (年龄）",
    "sex": "Sex （性别）",
    "cnlc": "CNLC Stage",
    "bclc": "BCLC Stage",
    "gtv": "GTV size (肿瘤大小 体积）volume  in cm3",
    "total_dose": "Total Dose (剂量）Gy*f",
    "bed": "BED",
    "eqd2": "EQD2",
    "scart_dose": "SCART Dose(剂量)",
    "scart_fx": "SCART  F",
    "os_event": "生存情况（1，0）",
    "os_months_rt": "Post-SCART survival days（放疗后存活时长）",
    "immuno_yn": "围放疗期免疫（前1m后3m)Y or N",
    "targeted_yn": "围放疗期靶向（前1m后3m)Y or N",
    "interv_yn": "围放疗期介入（前1m后3m)Y or N",
    "chemo_yn": "围放疗期系统化疗（前1m后3m)Y or N",
    "scart_start": "SCART治疗日期",
    "scart_end": "末次SCART日期",
    "death_date": "死亡日期",
    "last_fu": "末次随访日期",
}


def load_data() -> pd.DataFrame:
    df = pd.read_excel(DATA_DIR / "SCART 03092026.xlsx", sheet_name="生存数据")
    df.columns = [str(c).strip() for c in df.columns]
    inv_col = {v: k for k, v in COL.items() if v in df.columns}
    df = df.rename(columns=inv_col)

    for c in ["age", "gtv", "total_dose", "bed", "eqd2", "scart_dose", "scart_fx",
              "os_event", "os_months_rt", "immuno_yn", "targeted_yn", "interv_yn", "chemo_yn"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Flip event coding: source 1=alive 0=dead → KM 1=event(death)
    df["os_event"] = 1 - df["os_event"]

    # Parse dates
    for dcol in ["scart_start", "scart_end", "death_date", "last_fu"]:
        if dcol in df.columns:
            df[dcol] = pd.to_datetime(df[dcol], errors="coerce")

    # V2 OS formula: endpoint = death_date if present, else last_fu
    endpoint = df["death_date"].where(df["death_date"].notna(), df["last_fu"])
    df["os_months"] = (endpoint - df["scart_start"]).dt.days / 30.44

    # Data correction: death_date present → os_event must be 1
    df.loc[df["death_date"].notna(), "os_event"] = 1

    # Groups
    df["immuno_group"] = df["immuno_yn"].apply(
        lambda x: "SCART+IO" if x == 1 else "SCART Alone"
    )
    df["immuno_num"] = df["immuno_yn"].apply(lambda x: 1 if x == 1 else 0)

    # BCLC ordinal
    bclc_map = {"A": 1, "B": 2, "C": 3, "D": 4}
    df["bclc_ord"] = df["bclc"].map(bclc_map)

    # Filter to valid OS data
    valid = df.dropna(subset=["os_months", "os_event", "immuno_yn"]).copy()
    valid = valid[valid["os_months"] > 0]

    return valid


# ═══════════════════════════════════════════════════════════════════════════
#  1. PROPENSITY SCORE MATCHING
# ═══════════════════════════════════════════════════════════════════════════

def compute_propensity_scores(df: pd.DataFrame, covariates: list[str]) -> pd.Series:
    """Logistic regression propensity score for P(IO=1 | covariates)."""
    complete = df.dropna(subset=covariates + ["immuno_num"]).copy()
    X = complete[covariates].values
    y = complete["immuno_num"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    lr = LogisticRegression(max_iter=1000, solver="lbfgs")
    lr.fit(X_scaled, y)
    ps = lr.predict_proba(X_scaled)[:, 1]

    return pd.Series(ps, index=complete.index, name="ps")


def nearest_neighbor_match(df: pd.DataFrame, ps: pd.Series,
                           caliper: float = 0.2) -> pd.DataFrame:
    """1:1 nearest-neighbor matching without replacement, with caliper."""
    matched = df.loc[ps.index].copy()
    matched["ps"] = ps

    treated = matched[matched["immuno_num"] == 1].copy()
    control = matched[matched["immuno_num"] == 0].copy()

    if len(treated) == 0 or len(control) == 0:
        return pd.DataFrame()

    # Fit nearest neighbors on control PS
    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(control[["ps"]].values)

    distances, indices = nn.kneighbors(treated[["ps"]].values)

    # Apply caliper (in SD of PS)
    ps_sd = ps.std()
    caliper_abs = caliper * ps_sd

    matched_pairs = []
    used_controls = set()

    # Sort treated by distance (greedy matching)
    order = np.argsort(distances.ravel())
    for rank in order:
        t_idx = treated.index[rank]
        c_pos = indices[rank, 0]
        c_idx = control.index[c_pos]
        dist = distances[rank, 0]

        if dist > caliper_abs:
            continue
        if c_idx in used_controls:
            continue

        matched_pairs.append((t_idx, c_idx))
        used_controls.add(c_idx)

    if not matched_pairs:
        return pd.DataFrame()

    t_indices = [p[0] for p in matched_pairs]
    c_indices = [p[1] for p in matched_pairs]
    matched_df = pd.concat([matched.loc[t_indices], matched.loc[c_indices]])
    matched_df["matched"] = True

    return matched_df


def compute_smd(treated: pd.Series, control: pd.Series) -> float:
    """Standardized mean difference."""
    pooled_sd = np.sqrt((treated.var() + control.var()) / 2)
    if pooled_sd == 0:
        return 0.0
    return (treated.mean() - control.mean()) / pooled_sd


def psm_balance_table(df: pd.DataFrame, matched_df: pd.DataFrame,
                      covariates: list[str]) -> pd.DataFrame:
    """Covariate balance before and after matching."""
    rows = []
    for cov in covariates:
        t_before = df.loc[df["immuno_num"] == 1, cov].dropna()
        c_before = df.loc[df["immuno_num"] == 0, cov].dropna()
        smd_before = compute_smd(t_before, c_before)

        if len(matched_df) > 0:
            t_after = matched_df.loc[matched_df["immuno_num"] == 1, cov].dropna()
            c_after = matched_df.loc[matched_df["immuno_num"] == 0, cov].dropna()
            smd_after = compute_smd(t_after, c_after)
        else:
            t_after = pd.Series(dtype=float)
            c_after = pd.Series(dtype=float)
            smd_after = np.nan

        rows.append({
            "Covariate": cov,
            "Mean_IO_before": round(t_before.mean(), 3),
            "Mean_Alone_before": round(c_before.mean(), 3),
            "SMD_before": round(smd_before, 4),
            "Balanced_before": abs(smd_before) < 0.2,
            "Mean_IO_after": round(t_after.mean(), 3) if len(t_after) > 0 else np.nan,
            "Mean_Alone_after": round(c_after.mean(), 3) if len(c_after) > 0 else np.nan,
            "SMD_after": round(smd_after, 4) if not np.isnan(smd_after) else np.nan,
            "Balanced_after": abs(smd_after) < 0.2 if not np.isnan(smd_after) else np.nan,
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
#  2. IPTW (Inverse Probability of Treatment Weighting)
# ═══════════════════════════════════════════════════════════════════════════

def compute_iptw_weights(ps: pd.Series, treatment: pd.Series) -> pd.Series:
    """Compute stabilized IPTW weights."""
    # Stabilized weights
    p_treat = treatment.mean()
    weights = pd.Series(np.nan, index=ps.index)
    weights[treatment == 1] = p_treat / ps[treatment == 1]
    weights[treatment == 0] = (1 - p_treat) / (1 - ps[treatment == 0])
    # Truncate extreme weights at 99th percentile
    cap = weights.quantile(0.99)
    weights = weights.clip(upper=cap)
    return weights


# ═══════════════════════════════════════════════════════════════════════════
#  3. COX MODELS
# ═══════════════════════════════════════════════════════════════════════════

def adjusted_cox_models(df: pd.DataFrame) -> pd.DataFrame:
    """Multiple Cox regression models with increasing adjustment."""
    results = []

    # Model 1: Unadjusted
    m1_data = df[["os_months", "os_event", "immuno_num"]].dropna()
    m1_data = m1_data[m1_data["os_months"] > 0]
    cph = CoxPHFitter()
    cph.fit(m1_data, duration_col="os_months", event_col="os_event")
    s = cph.summary.loc["immuno_num"]
    results.append({
        "Model": "Unadjusted",
        "Covariate": "immuno (IO vs Alone)",
        "HR": round(s["exp(coef)"], 4),
        "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
        "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
        "p": round(s["p"], 4),
        "N": len(m1_data),
        "Events": int(m1_data["os_event"].sum()),
        "Concordance": round(cph.concordance_index_, 4),
    })

    # Model 2: Adjusted for age
    covs = ["immuno_num", "age"]
    m2_data = df[["os_months", "os_event"] + covs].dropna()
    m2_data = m2_data[m2_data["os_months"] > 0]
    cph = CoxPHFitter()
    cph.fit(m2_data, duration_col="os_months", event_col="os_event")
    for cov in covs:
        s = cph.summary.loc[cov]
        results.append({
            "Model": "Adjusted (age)",
            "Covariate": cov if cov != "immuno_num" else "immuno (IO vs Alone)",
            "HR": round(s["exp(coef)"], 4),
            "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
            "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
            "p": round(s["p"], 4),
            "N": len(m2_data),
            "Events": int(m2_data["os_event"].sum()),
            "Concordance": round(cph.concordance_index_, 4),
        })

    # Model 3: Adjusted for age + GTV + BCLC (V2's model)
    covs = ["immuno_num", "age", "gtv", "bclc_ord"]
    m3_data = df[["os_months", "os_event"] + covs].dropna()
    m3_data = m3_data[m3_data["os_months"] > 0]
    if len(m3_data) >= 10:
        cph = CoxPHFitter()
        cph.fit(m3_data, duration_col="os_months", event_col="os_event")
        for cov in covs:
            s = cph.summary.loc[cov]
            results.append({
                "Model": "Adjusted (age+GTV+BCLC)",
                "Covariate": cov if cov != "immuno_num" else "immuno (IO vs Alone)",
                "HR": round(s["exp(coef)"], 4),
                "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
                "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
                "p": round(s["p"], 4),
                "N": len(m3_data),
                "Events": int(m3_data["os_event"].sum()),
                "Concordance": round(cph.concordance_index_, 4),
            })

    # Model 4: Adjusted for age + GTV + BCLC + targeted + intervention
    covs = ["immuno_num", "age", "gtv", "bclc_ord", "targeted_yn", "interv_yn"]
    m4_data = df[["os_months", "os_event"] + covs].dropna()
    m4_data = m4_data[m4_data["os_months"] > 0]
    if len(m4_data) >= 15:
        cph = CoxPHFitter()
        cph.fit(m4_data, duration_col="os_months", event_col="os_event")
        for cov in covs:
            s = cph.summary.loc[cov]
            results.append({
                "Model": "Fully adjusted",
                "Covariate": cov if cov != "immuno_num" else "immuno (IO vs Alone)",
                "HR": round(s["exp(coef)"], 4),
                "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
                "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
                "p": round(s["p"], 4),
                "N": len(m4_data),
                "Events": int(m4_data["os_event"].sum()),
                "Concordance": round(cph.concordance_index_, 4),
            })

    # Model 5: Stratified by BCLC (within-stratum comparison)
    strata_data = df[["os_months", "os_event", "immuno_num", "bclc_ord"]].dropna()
    strata_data = strata_data[strata_data["os_months"] > 0]
    if len(strata_data) >= 10:
        cph = CoxPHFitter()
        cph.fit(strata_data, duration_col="os_months", event_col="os_event",
                strata=["bclc_ord"])
        s = cph.summary.loc["immuno_num"]
        results.append({
            "Model": "Stratified by BCLC",
            "Covariate": "immuno (IO vs Alone)",
            "HR": round(s["exp(coef)"], 4),
            "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
            "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
            "p": round(s["p"], 4),
            "N": len(strata_data),
            "Events": int(strata_data["os_event"].sum()),
            "Concordance": round(cph.concordance_index_, 4),
        })

    return pd.DataFrame(results)


def psm_cox(matched_df: pd.DataFrame) -> pd.DataFrame:
    """Cox regression on PSM-matched cohort."""
    if len(matched_df) < 4:
        return pd.DataFrame()

    results = []
    m_data = matched_df[["os_months", "os_event", "immuno_num"]].dropna()
    m_data = m_data[m_data["os_months"] > 0]
    if len(m_data) < 4:
        return pd.DataFrame()

    cph = CoxPHFitter()
    cph.fit(m_data, duration_col="os_months", event_col="os_event")
    s = cph.summary.loc["immuno_num"]
    results.append({
        "Model": "PSM-matched (unadjusted)",
        "Covariate": "immuno (IO vs Alone)",
        "HR": round(s["exp(coef)"], 4),
        "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
        "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
        "p": round(s["p"], 4),
        "N": len(m_data),
        "Events": int(m_data["os_event"].sum()),
        "Concordance": round(cph.concordance_index_, 4),
    })

    # PSM + age adjustment (doubly robust)
    covs = ["immuno_num", "age"]
    m_data2 = matched_df[["os_months", "os_event"] + covs].dropna()
    m_data2 = m_data2[m_data2["os_months"] > 0]
    if len(m_data2) >= 6:
        cph = CoxPHFitter()
        cph.fit(m_data2, duration_col="os_months", event_col="os_event")
        for cov in covs:
            s = cph.summary.loc[cov]
            results.append({
                "Model": "PSM + age adjusted (doubly robust)",
                "Covariate": cov if cov != "immuno_num" else "immuno (IO vs Alone)",
                "HR": round(s["exp(coef)"], 4),
                "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
                "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
                "p": round(s["p"], 4),
                "N": len(m_data2),
                "Events": int(m_data2["os_event"].sum()),
                "Concordance": round(cph.concordance_index_, 4),
            })

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════════════
#  4. SUBGROUP ANALYSES
# ═══════════════════════════════════════════════════════════════════════════

def bclc_subgroup_km(df: pd.DataFrame) -> pd.DataFrame:
    """IO vs Alone KM within each BCLC stage."""
    rows = []
    for bclc in sorted(df["bclc"].dropna().unique()):
        sub = df[df["bclc"] == bclc]
        for gname in ["SCART+IO", "SCART Alone"]:
            gdf = sub[sub["immuno_group"] == gname]
            gdf = gdf.dropna(subset=["os_months", "os_event"])
            gdf = gdf[gdf["os_months"] > 0]
            if len(gdf) < 1:
                rows.append({
                    "BCLC": bclc, "Group": gname, "N": 0,
                    "Events": 0, "mOS": "N/A", "1yr_OS": "N/A",
                })
                continue

            kmf = KaplanMeierFitter()
            kmf.fit(gdf["os_months"], gdf["os_event"].astype(int))
            m = kmf.median_survival_time_
            yr1 = f"{kmf.predict(12)*100:.0f}%" if gdf["os_months"].max() >= 12 else "N/A"

            rows.append({
                "BCLC": bclc,
                "Group": gname,
                "N": len(gdf),
                "Events": int(gdf["os_event"].sum()),
                "mOS": f"{m:.2f}" if np.isfinite(m) else "NR",
                "1yr_OS": yr1,
            })

        # Log-rank within BCLC
        io = sub[(sub["immuno_group"] == "SCART+IO")].dropna(subset=["os_months", "os_event"])
        io = io[io["os_months"] > 0]
        alone = sub[(sub["immuno_group"] == "SCART Alone")].dropna(subset=["os_months", "os_event"])
        alone = alone[alone["os_months"] > 0]
        if len(io) >= 2 and len(alone) >= 2:
            lr = logrank_test(io["os_months"], alone["os_months"],
                              io["os_event"].astype(int), alone["os_event"].astype(int))
            rows[-1]["log_rank_p"] = round(lr.p_value, 4)
            rows[-2]["log_rank_p"] = round(lr.p_value, 4)

    return pd.DataFrame(rows)


def interaction_test(df: pd.DataFrame) -> pd.DataFrame:
    """Test for IO × subgroup interactions."""
    results = []

    for label, col, threshold in [
        ("Age (<65 vs ≥65)", "age", 65),
        ("GTV (≤median vs >median)", "gtv", df["gtv"].median()),
    ]:
        sub = df.dropna(subset=["os_months", "os_event", "immuno_num", col])
        sub = sub[sub["os_months"] > 0].copy()
        sub["subgroup"] = (sub[col] > threshold).astype(int)
        sub["interaction"] = sub["immuno_num"] * sub["subgroup"]

        if len(sub) < 10:
            continue

        cph = CoxPHFitter()
        cph.fit(sub[["os_months", "os_event", "immuno_num", "subgroup", "interaction"]],
                duration_col="os_months", event_col="os_event")

        s_main = cph.summary.loc["immuno_num"]
        s_int = cph.summary.loc["interaction"]

        results.append({
            "Subgroup": label,
            "IO_HR": round(s_main["exp(coef)"], 4),
            "IO_p": round(s_main["p"], 4),
            "Interaction_HR": round(s_int["exp(coef)"], 4),
            "Interaction_p": round(s_int["p"], 4),
            "N": len(sub),
        })

    # BCLC B vs C interaction
    sub = df[df["bclc"].isin(["B", "C"])].dropna(subset=["os_months", "os_event", "immuno_num"])
    sub = sub[sub["os_months"] > 0].copy()
    sub["bclc_c"] = (sub["bclc"] == "C").astype(int)
    sub["interaction"] = sub["immuno_num"] * sub["bclc_c"]
    if len(sub) >= 10:
        cph = CoxPHFitter()
        cph.fit(sub[["os_months", "os_event", "immuno_num", "bclc_c", "interaction"]],
                duration_col="os_months", event_col="os_event")
        s_main = cph.summary.loc["immuno_num"]
        s_int = cph.summary.loc["interaction"]
        results.append({
            "Subgroup": "BCLC (B vs C)",
            "IO_HR": round(s_main["exp(coef)"], 4),
            "IO_p": round(s_main["p"], 4),
            "Interaction_HR": round(s_int["exp(coef)"], 4),
            "Interaction_p": round(s_int["p"], 4),
            "N": len(sub),
        })

    return pd.DataFrame(results)


def restricted_mean_survival(df: pd.DataFrame, tau: float = 24.0) -> pd.DataFrame:
    """Restricted Mean Survival Time (RMST) comparison at tau months."""
    rows = []
    for gname in ["SCART+IO", "SCART Alone"]:
        gdf = df[df["immuno_group"] == gname].dropna(subset=["os_months", "os_event"])
        gdf = gdf[gdf["os_months"] > 0]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int))

        # RMST = area under KM curve up to tau
        timeline = kmf.survival_function_at_times(
            np.linspace(0, min(tau, gdf["os_months"].max()), 200)
        )
        dt = min(tau, gdf["os_months"].max()) / 200
        rmst = timeline.values.sum() * dt

        rows.append({
            "Group": gname,
            "N": len(gdf),
            "Events": int(gdf["os_event"].sum()),
            "RMST_months": round(rmst, 2),
            "tau": tau,
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
#  5. IPTW KM & COX
# ═══════════════════════════════════════════════════════════════════════════

def iptw_cox(df: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Weighted Cox regression using IPTW."""
    results = []
    w_data = df.loc[weights.index, ["os_months", "os_event", "immuno_num"]].copy()
    w_data["weight"] = weights
    w_data = w_data.dropna()
    w_data = w_data[w_data["os_months"] > 0]

    if len(w_data) < 6:
        return pd.DataFrame()

    cph = CoxPHFitter()
    cph.fit(w_data[["os_months", "os_event", "immuno_num"]], duration_col="os_months",
            event_col="os_event", weights_col=None)  # lifelines doesn't directly support IPTW in fit

    # Manually use robust weights via weighted data
    # For lifelines, we approximate by using weights parameter
    try:
        cph_w = CoxPHFitter()
        cph_w.fit(w_data[["os_months", "os_event", "immuno_num", "weight"]],
                  duration_col="os_months", event_col="os_event",
                  weights_col="weight", robust=True)
        s = cph_w.summary.loc["immuno_num"]
        results.append({
            "Model": "IPTW-weighted Cox",
            "Covariate": "immuno (IO vs Alone)",
            "HR": round(s["exp(coef)"], 4),
            "HR_lower_CI": round(s["exp(coef) lower 95%"], 4),
            "HR_upper_CI": round(s["exp(coef) upper 95%"], 4),
            "p": round(s["p"], 4),
            "N": len(w_data),
            "Events": int(w_data["os_event"].sum()),
            "Concordance": round(cph_w.concordance_index_, 4),
        })
    except Exception as e:
        print(f"  IPTW Cox failed: {e}")

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════════════
#  6. FIGURES
# ═══════════════════════════════════════════════════════════════════════════

def fig_psm_balance(balance_df: pd.DataFrame):
    """Love plot: SMD before and after matching."""
    fig, ax = plt.subplots(figsize=(8, 5))
    y = range(len(balance_df))
    labels = balance_df["Covariate"].values

    ax.scatter(balance_df["SMD_before"].abs(), y, color=COLOR_IO, s=100,
               marker="o", label="Before matching", zorder=3)
    if "SMD_after" in balance_df.columns and balance_df["SMD_after"].notna().any():
        ax.scatter(balance_df["SMD_after"].abs(), y, color=COLOR_ALONE, s=100,
                   marker="D", label="After matching", zorder=3)

    # Connect before→after with lines
    for i in range(len(balance_df)):
        if pd.notna(balance_df.iloc[i]["SMD_after"]):
            ax.plot([abs(balance_df.iloc[i]["SMD_before"]), abs(balance_df.iloc[i]["SMD_after"])],
                    [i, i], color="gray", linewidth=1, alpha=0.5)

    ax.axvline(0.1, color="green", linewidth=1, linestyle="--", label="SMD = 0.1")
    ax.axvline(0.2, color="orange", linewidth=1, linestyle="--", label="SMD = 0.2")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Absolute Standardized Mean Difference")
    ax.set_title("PSM Covariate Balance: Before vs After Matching")
    ax.legend(loc="upper right")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "Fig20_PSM_Balance.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig20_PSM_Balance.png")


def fig_psm_km(matched_df: pd.DataFrame):
    """KM curves on PSM-matched cohort."""
    if len(matched_df) < 4:
        print("  Fig21 — skipped (insufficient matched pairs)")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    kmfs = {}

    for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
        gdf = matched_df[matched_df["immuno_group"] == gname]
        gdf = gdf.dropna(subset=["os_months", "os_event"])
        gdf = gdf[gdf["os_months"] > 0]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int), label=f"{gname} (n={len(gdf)})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)
        kmfs[gname] = kmf

    # Log-rank on matched
    io = matched_df[matched_df["immuno_group"] == "SCART+IO"].dropna(subset=["os_months", "os_event"])
    io = io[io["os_months"] > 0]
    alone = matched_df[matched_df["immuno_group"] == "SCART Alone"].dropna(subset=["os_months", "os_event"])
    alone = alone[alone["os_months"] > 0]
    if len(io) > 1 and len(alone) > 1:
        lr = logrank_test(io["os_months"], alone["os_months"],
                          io["os_event"].astype(int), alone["os_event"].astype(int))
        ax.text(0.98, 0.98, f"Log-rank p = {lr.p_value:.4f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=11,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

        # Add mOS annotation
        for gname, kmf_g in kmfs.items():
            m = kmf_g.median_survival_time_
            mstr = f"{m:.1f}" if np.isfinite(m) else "NR"
            color = COLOR_IO if "IO" in gname else COLOR_ALONE
            # Find y position at median
            if np.isfinite(m):
                ax.axhline(0.5, color="gray", linewidth=0.5, linestyle=":", alpha=0.3)

    if kmfs:
        add_at_risk_counts(*kmfs.values(), ax=ax)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall Survival Probability")
    ax.set_title("PSM-Matched Overall Survival: SCART+IO vs SCART Alone")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "Fig21_PSM_Matched_KM.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig21_PSM_Matched_KM.png")


def fig_bclc_c_km(df: pd.DataFrame):
    """KM curves for BCLC C subgroup: IO vs Alone."""
    bclc_c = df[df["bclc"] == "C"].dropna(subset=["os_months", "os_event"])
    bclc_c = bclc_c[bclc_c["os_months"] > 0]

    fig, ax = plt.subplots(figsize=(8, 6))
    kmfs = {}

    for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
        gdf = bclc_c[bclc_c["immuno_group"] == gname]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int), label=f"{gname} (n={len(gdf)})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)
        kmfs[gname] = kmf

        m = kmf.median_survival_time_
        mstr = f"{m:.1f} mo" if np.isfinite(m) else "NR"
        print(f"    BCLC-C {gname}: N={len(gdf)}, Events={int(gdf['os_event'].sum())}, mOS={mstr}")

    io_c = bclc_c[bclc_c["immuno_group"] == "SCART+IO"]
    alone_c = bclc_c[bclc_c["immuno_group"] == "SCART Alone"]
    if len(io_c) > 1 and len(alone_c) > 1:
        lr = logrank_test(io_c["os_months"], alone_c["os_months"],
                          io_c["os_event"].astype(int), alone_c["os_event"].astype(int))
        ax.text(0.98, 0.98, f"Log-rank p = {lr.p_value:.4f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=11,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    if kmfs:
        add_at_risk_counts(*kmfs.values(), ax=ax)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall Survival Probability")
    ax.set_title("BCLC-C Subgroup: SCART+IO vs SCART Alone")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "Fig22_BCLC_C_IO_vs_Alone.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig22_BCLC_C_IO_vs_Alone.png")


def fig_forest_all_models(cox_results: pd.DataFrame, psm_results: pd.DataFrame,
                          iptw_results: pd.DataFrame):
    """Comprehensive forest plot of IO HR across all models."""
    # Collect IO HRs from all models
    all_io = []

    for df_r, source in [(cox_results, ""), (psm_results, ""), (iptw_results, "")]:
        if df_r is None or len(df_r) == 0:
            continue
        io_rows = df_r[df_r["Covariate"].str.contains("immuno", case=False, na=False)]
        for _, r in io_rows.iterrows():
            all_io.append(r.to_dict())

    if not all_io:
        print("  Fig23 — skipped")
        return

    fig, ax = plt.subplots(figsize=(10, max(4, len(all_io) * 0.7)))
    y = range(len(all_io))
    labels = [f"{r['Model']}" for r in all_io]
    hrs = [r["HR"] for r in all_io]
    lo = [r["HR_lower_CI"] for r in all_io]
    hi = [r["HR_upper_CI"] for r in all_io]
    ps_vals = [r["p"] for r in all_io]
    ns = [r.get("N", "") for r in all_io]

    ax.errorbar(hrs, y, xerr=[np.array(hrs) - np.array(lo), np.array(hi) - np.array(hrs)],
                fmt="D", color=COLOR_IO, markersize=8, capsize=4, linewidth=2)
    ax.axvline(1, color="black", linewidth=0.8, linestyle="--")
    ax.axvspan(0, 1, alpha=0.05, color="green")  # IO protective zone

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Hazard Ratio (IO vs Alone)")
    ax.set_title("Immunotherapy Effect on OS — All Models\n(HR < 1 favors IO)")
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())

    for i in range(len(all_io)):
        ax.text(max(hi) * 1.4, i,
                f"HR={hrs[i]:.2f} [{lo[i]:.2f}-{hi[i]:.2f}]  p={ps_vals[i]:.3f}  n={ns[i]}",
                va="center", fontsize=8)

    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "Fig23_IO_HR_All_Models.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig23_IO_HR_All_Models.png")


def fig_bclc_forest(df: pd.DataFrame):
    """Forest plot of IO HR within each BCLC subgroup."""
    subgroups = []

    for bclc in sorted(df["bclc"].dropna().unique()):
        sub = df[df["bclc"] == bclc].dropna(subset=["os_months", "os_event", "immuno_num"])
        sub = sub[sub["os_months"] > 0]
        if len(sub) < 4 or sub["immuno_num"].nunique() < 2:
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(sub[["os_months", "os_event", "immuno_num"]],
                    duration_col="os_months", event_col="os_event")
            s = cph.summary.loc["immuno_num"]
            subgroups.append({
                "Subgroup": f"BCLC {bclc}",
                "HR": s["exp(coef)"],
                "lo": s["exp(coef) lower 95%"],
                "hi": s["exp(coef) upper 95%"],
                "p": s["p"],
                "N": len(sub),
                "N_IO": int(sub["immuno_num"].sum()),
                "N_Alone": len(sub) - int(sub["immuno_num"].sum()),
            })
        except Exception:
            pass

    if not subgroups:
        print("  Fig24 — skipped")
        return

    fig, ax = plt.subplots(figsize=(9, max(3, len(subgroups) * 1.0)))
    y = range(len(subgroups))
    labels = [f"{s['Subgroup']} (IO={s['N_IO']}, Alone={s['N_Alone']})" for s in subgroups]
    hrs = [s["HR"] for s in subgroups]
    lo = [s["lo"] for s in subgroups]
    hi = [s["hi"] for s in subgroups]
    ps_vals = [s["p"] for s in subgroups]

    ax.errorbar(hrs, y, xerr=[np.array(hrs) - np.array(lo), np.array(hi) - np.array(hrs)],
                fmt="D", color=COLOR_IO, markersize=10, capsize=5, linewidth=2)
    ax.axvline(1, color="black", linewidth=0.8, linestyle="--")
    ax.axvspan(0, 1, alpha=0.05, color="green")

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Hazard Ratio (IO vs Alone)")
    ax.set_title("IO Effect by BCLC Subgroup\n(HR < 1 favors IO)")
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())

    for i in range(len(subgroups)):
        ax.text(max(hi) * 1.5, i,
                f"HR={hrs[i]:.2f} [{lo[i]:.2f}-{hi[i]:.2f}]  p={ps_vals[i]:.3f}",
                va="center", fontsize=9)

    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "Fig24_BCLC_Subgroup_Forest.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig24_BCLC_Subgroup_Forest.png")


# ═══════════════════════════════════════════════════════════════════════════
#  COMPARISON WITH V2
# ═══════════════════════════════════════════════════════════════════════════

def compare_with_v2(balance_df: pd.DataFrame, cox_df: pd.DataFrame) -> pd.DataFrame:
    """Compare V3 matched results with V2."""
    rows = []

    # Load V2 reference
    try:
        v2_psm = pd.read_excel(OLD_REPORT, sheet_name="PSM_Balance")
        v2_cox = pd.read_excel(OLD_REPORT, sheet_name="Stratified_Cox")
    except Exception:
        return pd.DataFrame()

    # PSM balance comparison
    for _, v3_row in balance_df.iterrows():
        cov = v3_row["Covariate"]
        v2_match = v2_psm[v2_psm["Covariate"] == cov]
        if len(v2_match) > 0:
            rows.append({
                "Metric": f"PSM SMD before ({cov})",
                "V2": v2_match.iloc[0].get("SMD_before", ""),
                "V3": v3_row["SMD_before"],
            })
            rows.append({
                "Metric": f"PSM SMD after ({cov})",
                "V2": v2_match.iloc[0].get("SMD_after", ""),
                "V3": v3_row.get("SMD_after", ""),
            })

    # Cox HR comparison
    v2_adj = v2_cox[v2_cox["Model"].str.contains("age", case=False, na=False)]
    v2_io = v2_adj[v2_adj["Covariate"].str.contains("immuno", case=False, na=False)]
    v3_adj = cox_df[cox_df["Model"].str.contains("age.*GTV.*BCLC", case=False, na=False)]
    v3_io = v3_adj[v3_adj["Covariate"].str.contains("immuno", case=False, na=False)]

    if len(v2_io) > 0 and len(v3_io) > 0:
        rows.append({
            "Metric": "Adjusted IO HR (age+GTV+BCLC)",
            "V2": f"{v2_io.iloc[0]['HR']:.4f}",
            "V3": f"{v3_io.iloc[0]['HR']:.4f}",
        })
        rows.append({
            "Metric": "Adjusted IO p-value",
            "V2": f"{v2_io.iloc[0]['p']:.4f}",
            "V3": f"{v3_io.iloc[0]['p']:.4f}",
        })

    # Stratified Cox comparison
    v2_strat = v2_cox[v2_cox["Model"].str.contains("Stratified", case=False, na=False)]
    v2_strat_io = v2_strat[v2_strat["Covariate"].str.contains("immuno", case=False, na=False)]
    v3_strat = cox_df[cox_df["Model"].str.contains("Stratified", case=False, na=False)]
    v3_strat_io = v3_strat[v3_strat["Covariate"].str.contains("immuno", case=False, na=False)]

    if len(v2_strat_io) > 0 and len(v3_strat_io) > 0:
        rows.append({
            "Metric": "Stratified by BCLC — IO HR",
            "V2": f"{v2_strat_io.iloc[0]['HR']:.4f}",
            "V3": f"{v3_strat_io.iloc[0]['HR']:.4f}",
        })
        rows.append({
            "Metric": "Stratified by BCLC — IO p",
            "V2": f"{v2_strat_io.iloc[0]['p']:.4f}",
            "V3": f"{v3_strat_io.iloc[0]['p']:.4f}",
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("SCART V3 MATCHED & ADJUSTED ANALYSIS")
    print("=" * 70)

    print("\nLoading data...")
    df = load_data()
    print(f"  Valid OS data: {len(df)} cases")
    print(f"  IO: {(df['immuno_num'] == 1).sum()}, Alone: {(df['immuno_num'] == 0).sum()}")

    results: dict[str, pd.DataFrame] = {}

    # ── 1. Propensity Score Matching ──────────────────────────────────────
    print("\n1. PROPENSITY SCORE MATCHING")
    covariates = ["age", "gtv", "bclc_ord"]
    ps_data = df.dropna(subset=covariates + ["immuno_num"])

    print(f"  Matching on: {covariates}")
    ps = compute_propensity_scores(ps_data, covariates)
    print(f"  PS range: {ps.min():.3f} - {ps.max():.3f}")

    matched_df = nearest_neighbor_match(ps_data, ps, caliper=0.25)
    n_io_matched = (matched_df["immuno_num"] == 1).sum() if len(matched_df) > 0 else 0
    n_alone_matched = (matched_df["immuno_num"] == 0).sum() if len(matched_df) > 0 else 0
    print(f"  Matched: {n_io_matched} IO + {n_alone_matched} Alone = {len(matched_df)} total")

    balance_df = psm_balance_table(ps_data, matched_df, covariates)
    results["PSM_Balance"] = balance_df
    print("\n  Covariate balance:")
    for _, row in balance_df.iterrows():
        print(f"    {row['Covariate']}: SMD {row['SMD_before']:.3f} → {row['SMD_after']:.3f}"
              f"  {'✓' if row['Balanced_after'] else '✗'}")

    # ── 2. PSM KM & Cox ──────────────────────────────────────────────────
    print("\n2. PSM-MATCHED SURVIVAL ANALYSIS")
    if len(matched_df) >= 4:
        for gname in ["SCART+IO", "SCART Alone"]:
            gdf = matched_df[matched_df["immuno_group"] == gname]
            gdf = gdf.dropna(subset=["os_months", "os_event"])
            gdf = gdf[gdf["os_months"] > 0]
            kmf = KaplanMeierFitter()
            kmf.fit(gdf["os_months"], gdf["os_event"].astype(int))
            m = kmf.median_survival_time_
            mstr = f"{m:.2f}" if np.isfinite(m) else "NR"
            print(f"  {gname}: N={len(gdf)}, Events={int(gdf['os_event'].sum())}, mOS={mstr}")

        psm_cox_df = psm_cox(matched_df)
        results["PSM_Cox"] = psm_cox_df
        for _, r in psm_cox_df.iterrows():
            if "immuno" in str(r.get("Covariate", "")):
                print(f"  {r['Model']}: HR={r['HR']:.3f} [{r['HR_lower_CI']:.3f}-{r['HR_upper_CI']:.3f}] p={r['p']:.4f}")
    else:
        psm_cox_df = pd.DataFrame()
        print("  Insufficient matched pairs")

    # ── 3. IPTW Analysis ──────────────────────────────────────────────────
    print("\n3. IPTW (INVERSE PROBABILITY WEIGHTING)")
    treatment = ps_data.loc[ps.index, "immuno_num"]
    weights = compute_iptw_weights(ps, treatment)
    print(f"  Weight range: {weights.min():.3f} - {weights.max():.3f}")
    print(f"  Weight mean: IO={weights[treatment == 1].mean():.3f}, Alone={weights[treatment == 0].mean():.3f}")

    iptw_cox_df = iptw_cox(ps_data, weights)
    results["IPTW_Cox"] = iptw_cox_df
    if len(iptw_cox_df) > 0:
        for _, r in iptw_cox_df.iterrows():
            print(f"  {r['Model']}: HR={r['HR']:.3f} [{r['HR_lower_CI']:.3f}-{r['HR_upper_CI']:.3f}] p={r['p']:.4f}")

    # ── 4. Adjusted Cox Models ────────────────────────────────────────────
    print("\n4. ADJUSTED COX REGRESSION MODELS")
    cox_df = adjusted_cox_models(df)
    results["Adjusted_Cox"] = cox_df
    for _, r in cox_df.iterrows():
        if "immuno" in str(r.get("Covariate", "")):
            print(f"  {r['Model']}: HR={r['HR']:.3f} [{r['HR_lower_CI']:.3f}-{r['HR_upper_CI']:.3f}] p={r['p']:.4f} (C={r['Concordance']:.3f})")

    # ── 5. BCLC Subgroup Analysis ─────────────────────────────────────────
    print("\n5. BCLC SUBGROUP ANALYSIS")
    bclc_km_df = bclc_subgroup_km(df)
    results["BCLC_Subgroup_KM"] = bclc_km_df
    for _, r in bclc_km_df.iterrows():
        lr_str = f"  p={r.get('log_rank_p', 'N/A')}" if pd.notna(r.get("log_rank_p")) else ""
        print(f"  BCLC {r['BCLC']} — {r['Group']}: N={r['N']}, Events={r['Events']}, mOS={r['mOS']}{lr_str}")

    # ── 6. Interaction Tests ──────────────────────────────────────────────
    print("\n6. INTERACTION TESTS")
    interact_df = interaction_test(df)
    results["Interaction_Tests"] = interact_df
    for _, r in interact_df.iterrows():
        print(f"  {r['Subgroup']}: IO HR={r['IO_HR']:.3f} (p={r['IO_p']:.3f}), "
              f"Interaction HR={r['Interaction_HR']:.3f} (p={r['Interaction_p']:.3f})")

    # ── 7. RMST ───────────────────────────────────────────────────────────
    print("\n7. RESTRICTED MEAN SURVIVAL TIME (τ=24 mo)")
    rmst_df = restricted_mean_survival(df, tau=24.0)
    results["RMST"] = rmst_df
    for _, r in rmst_df.iterrows():
        print(f"  {r['Group']}: RMST={r['RMST_months']:.2f} mo (N={r['N']}, Events={r['Events']})")

    # Also at 12 months
    print("\n   RMST (τ=12 mo)")
    rmst_12 = restricted_mean_survival(df, tau=12.0)
    results["RMST_12mo"] = rmst_12
    for _, r in rmst_12.iterrows():
        print(f"  {r['Group']}: RMST={r['RMST_months']:.2f} mo")

    # ── 8. V2 Comparison ─────────────────────────────────────────────────
    print("\n8. V2 vs V3 MATCHED ANALYSIS COMPARISON")
    v2_comp = compare_with_v2(balance_df, cox_df)
    results["V2_vs_V3_Matched"] = v2_comp
    for _, r in v2_comp.iterrows():
        print(f"  {r['Metric']}: V2={r['V2']}, V3={r['V3']}")

    # ── 9. Figures ────────────────────────────────────────────────────────
    print("\n9. GENERATING FIGURES")
    fig_psm_balance(balance_df)
    fig_psm_km(matched_df)
    fig_bclc_c_km(df)
    fig_forest_all_models(cox_df, psm_cox_df, iptw_cox_df)
    fig_bclc_forest(df)

    # ── Write Excel ───────────────────────────────────────────────────────
    print(f"\nWriting {OUTPUT_XLSX}...")
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        for sheet_name, sheet_df in results.items():
            if sheet_df is not None and len(sheet_df) > 0:
                sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    print(f"Done! {len(results)} sheets written to:\n  {OUTPUT_XLSX}")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY: IO EFFECT ACROSS ALL METHODS")
    print("=" * 70)
    print("  Method                          HR      95% CI            p")
    print("  " + "-" * 65)
    for df_r in [cox_df, psm_cox_df, iptw_cox_df]:
        if df_r is None or len(df_r) == 0:
            continue
        for _, r in df_r.iterrows():
            if "immuno" in str(r.get("Covariate", "")):
                print(f"  {r['Model']:<33} {r['HR']:.3f}   [{r['HR_lower_CI']:.3f}-{r['HR_upper_CI']:.3f}]   {r['p']:.4f}")

    print("\n  HR < 1 → IO is protective (reduces hazard of death)")
    print("  HR > 1 → IO is harmful")
    print("  p < 0.05 → statistically significant")


if __name__ == "__main__":
    main()
