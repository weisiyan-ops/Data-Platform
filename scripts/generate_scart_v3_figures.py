"""Generate all V3 figures for SCART HCC analysis — matches V2 figure set + new AICE3 plots.

Usage:
    python scripts/generate_scart_v3_figures.py
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

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OUT_DIR = DATA_DIR
SCART_FILE = DATA_DIR / "SCART 03092026.xlsx"
AICE_FILE = DATA_DIR / "liver_cases_aice3_results.csv"

# ── style ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": False,
})
COLOR_IO = "#E63946"
COLOR_ALONE = "#457B9D"
COLOR_BCLC = {"A": "#2A9D8F", "B": "#E9C46A", "C": "#E76F51", "D": "#264653"}
COLOR_GTV = {"small": "#457B9D", "large": "#E63946"}
PALETTE = ["#264653", "#2A9D8F", "#E9C46A", "#E76F51", "#E63946", "#457B9D"]


# ═══════════════════════════════════════════════════════════════════════════
#  DATA LOADING  (reuse logic from analyze_scart_v3.py)
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load and prepare all datasets."""
    # Survival
    surv = pd.read_excel(SCART_FILE, sheet_name="生存数据")
    surv.columns = [str(c).strip() for c in surv.columns]

    col_map = {
        "数据定位编号（患者-肿瘤-疗程）": "case_id",
        "ID": "patient_id",
        "中文名": "name",
        "Age (年龄）": "age",
        "Sex （性别）": "sex",
        "CNLC Stage": "cnlc",
        "BCLC Stage": "bclc",
        "GTV size (肿瘤大小 体积）volume  in cm3": "gtv",
        "Total Dose (剂量）Gy*f": "total_dose",
        "BED": "bed",
        "EQD2": "eqd2",
        "SCART Dose(剂量)": "scart_dose",
        "SCART  F": "scart_fx",
        "生存情况（1，0）": "os_event",
        "Post-SCART survival days（放疗后存活时长）": "os_months",
        "围放疗期免疫（前1m后3m)Y or N": "immuno_yn",
        "围放疗期靶向（前1m后3m)Y or N": "targeted_yn",
        "围放疗期介入（前1m后3m)Y or N": "interv_yn",
        "围放疗期系统化疗（前1m后3m)Y or N": "chemo_yn",
        "治疗前CP评分": "cp_pre",
        "治疗后1月CP评分": "cp_post",
        "SCART治疗日期": "scart_start",
        "末次SCART日期": "scart_end",
        "死亡日期": "death_date",
        "末次随访日期": "last_fu",
    }
    surv = surv.rename(columns={k: v for k, v in col_map.items() if k in surv.columns})

    for c in ["age", "gtv", "total_dose", "bed", "eqd2", "scart_dose", "scart_fx",
              "os_event", "os_months", "immuno_yn", "targeted_yn", "interv_yn", "chemo_yn"]:
        if c in surv.columns:
            surv[c] = pd.to_numeric(surv[c], errors="coerce")

    # Flip event coding: source 生存情况 1=alive 0=dead → KM convention 1=event(death)
    surv["os_event"] = 1 - surv["os_event"]

    # Parse date columns for per-course OS calculation (matches V2 formula)
    for dcol in ["scart_start", "scart_end", "death_date", "last_fu"]:
        if dcol in surv.columns:
            surv[dcol] = pd.to_datetime(surv[dcol], errors="coerce")

    # V2 OS formula: endpoint = death_date if present, else last_fu; then (endpoint - scart_start) / 30.44
    endpoint = surv["death_date"].where(surv["death_date"].notna(), surv["last_fu"])
    surv["os_months"] = (endpoint - surv["scart_start"]).dt.days / 30.44

    # Data correction: if death_date is present, patient died → os_event must be 1
    surv.loc[surv["death_date"].notna(), "os_event"] = 1

    surv["immuno_group"] = surv["immuno_yn"].apply(
        lambda x: "SCART+IO" if x == 1 else "SCART Alone"
    )

    # Tox grade
    tox_col = [c for c in surv.columns if "Toxicity" in c or "毒性" in c]
    if tox_col:
        surv["tox_grade"] = surv[tox_col[0]].apply(_parse_tox_grade)
    else:
        surv["tox_grade"] = 0

    # Response
    resp_col = [c for c in surv.columns if "Response Local" in c]
    if resp_col:
        surv["response_local"] = surv[resp_col[0]]

    median_gtv = surv["gtv"].median()
    surv["gtv_group"] = surv["gtv"].apply(
        lambda x: f"GTV > {median_gtv:.0f}" if pd.notna(x) and x > median_gtv else f"GTV <= {median_gtv:.0f}"
    )
    surv["_median_gtv"] = median_gtv

    # OAR
    oar = pd.read_excel(SCART_FILE, sheet_name="OAR", header=None)
    organ_row = oar.iloc[0].ffill()
    metric_row = oar.iloc[1]
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
    oar.columns = columns
    oar = oar.iloc[2:].reset_index(drop=True)
    for c in oar.columns:
        if c not in ("col_0", "ID", "中文名", "末次放疗时间"):
            oar[c] = pd.to_numeric(oar[c], errors="coerce")
    # Rename ID col
    if "col_0" in oar.columns:
        oar = oar.rename(columns={"col_0": "case_id"})
    id_to_immuno = dict(zip(surv["case_id"].astype(str), surv["immuno_group"]))
    oar["immuno_group"] = oar["case_id"].astype(str).map(id_to_immuno)

    # Imaging
    img = pd.read_excel(SCART_FILE, sheet_name="影像及肿瘤尺寸", header=None)
    header_row = img.iloc[0]
    cols = []
    for i, val in enumerate(header_row):
        s = str(val).strip() if pd.notna(val) else f"col_{i}"
        if s.startswith("版本"):
            s = "case_id"
        cols.append(s)
    img.columns = cols
    img = img.iloc[1:].reset_index(drop=True)

    # AICE3
    aice = pd.read_csv(AICE_FILE)

    return surv, oar, img, aice


def _parse_tox_grade(val) -> int:
    if pd.isna(val) or str(val).strip() == "":
        return 0
    text = str(val)
    grades = []
    for g in ["1", "2", "3", "4", "5"]:
        if f"{g}级" in text:
            grades.append(int(g))
    return max(grades) if grades else 0


def _get_valid_os(df):
    """Get cases with valid OS data."""
    return df.dropna(subset=["os_months", "os_event"]).query("os_months > 0").copy()


# ═══════════════════════════════════════════════════════════════════════════
#  FIGURE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def fig1_os_km(surv):
    """Fig 1: OS Kaplan-Meier by immunotherapy group."""
    valid = _get_valid_os(surv)
    fig, ax = plt.subplots(figsize=(8, 6))

    kmfs = {}
    for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
        gdf = valid[valid["immuno_group"] == gname]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int), label=gname)
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)
        kmfs[gname] = kmf

    # Log-rank
    io = valid[valid["immuno_group"] == "SCART+IO"]
    alone = valid[valid["immuno_group"] == "SCART Alone"]
    if len(io) > 1 and len(alone) > 1:
        lr = logrank_test(io["os_months"], alone["os_months"],
                          io["os_event"].astype(int), alone["os_event"].astype(int))
        ax.text(0.98, 0.98, f"Log-rank p = {lr.p_value:.4f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=11, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    if kmfs:
        add_at_risk_counts(*kmfs.values(), ax=ax)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall Survival Probability")
    ax.set_title("Overall Survival: SCART+IO vs SCART Alone")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig1_OS_KM.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig1_OS_KM.png")


def fig2_baseline_forest(surv):
    """Fig 2: Forest plot of baseline characteristics (IO vs Alone)."""
    valid = _get_valid_os(surv)
    io = valid[valid["immuno_group"] == "SCART+IO"]
    alone = valid[valid["immuno_group"] == "SCART Alone"]

    comparisons = []
    for label, col in [("Age", "age"), ("GTV (cm3)", "gtv"), ("Total Dose (Gy)", "total_dose"),
                       ("BED", "bed"), ("EQD2", "eqd2")]:
        a, b = io[col].dropna(), alone[col].dropna()
        if len(a) > 1 and len(b) > 1:
            # Standardized mean difference
            pooled_sd = np.sqrt(((len(a)-1)*a.std()**2 + (len(b)-1)*b.std()**2) / (len(a)+len(b)-2))
            smd = (a.mean() - b.mean()) / pooled_sd if pooled_sd > 0 else 0
            _, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            comparisons.append({"label": label, "smd": smd, "p": p,
                                "io_med": a.median(), "alone_med": b.median()})

    # Categorical
    for label, col, cats in [("Male sex (%)", "sex", ["男"]),
                             ("Targeted (%)", "targeted_yn", [1.0]),
                             ("Intervention (%)", "interv_yn", [1.0]),
                             ("Chemo (%)", "chemo_yn", [1.0])]:
        a_pct = io[col].isin(cats).mean()
        b_pct = alone[col].isin(cats).mean()
        smd = (a_pct - b_pct)
        a_yes, a_no = io[col].isin(cats).sum(), (~io[col].isin(cats)).sum()
        b_yes, b_no = alone[col].isin(cats).sum(), (~alone[col].isin(cats)).sum()
        _, p = stats.fisher_exact([[a_yes, a_no], [b_yes, b_no]])
        comparisons.append({"label": label, "smd": smd, "p": p,
                            "io_med": f"{a_pct*100:.0f}%", "alone_med": f"{b_pct*100:.0f}%"})

    fig, ax = plt.subplots(figsize=(8, 6))
    labels = [c["label"] for c in comparisons]
    smds = [c["smd"] for c in comparisons]
    colors = [COLOR_IO if s > 0 else COLOR_ALONE for s in smds]
    y_pos = range(len(labels))

    ax.barh(y_pos, smds, color=colors, height=0.6, alpha=0.8)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.axvline(-0.2, color="gray", linewidth=0.5, linestyle=":")
    ax.axvline(0.2, color="gray", linewidth=0.5, linestyle=":")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Standardized Mean Difference (IO − Alone)")
    ax.set_title("Baseline Covariate Balance: SCART+IO vs SCART Alone")

    for i, c in enumerate(comparisons):
        ax.text(max(smds) + 0.05, i, f"p={c['p']:.3f}", va="center", fontsize=9)

    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig2_Baseline_Forest.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig2_Baseline_Forest.png")


def fig3_oar_boxplots(oar):
    """Fig 3: OAR dose box plots."""
    dose_cols = [c for c in oar.columns if any(k in c for k in ["Dmax", "D30cc", "D5cc", "D20cc", "D700cc"])]
    dose_cols = [c for c in dose_cols if oar[c].notna().sum() > 5]

    if not dose_cols:
        print("  Fig3 — skipped (no OAR dose data)")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    data = [oar[c].dropna().values for c in dose_cols]
    short_labels = []
    for c in dose_cols:
        parts = c.split("_")
        short_labels.append(f"{parts[0]}\n{parts[1]}" if len(parts) > 1 else c[:15])

    bp = ax.boxplot(data, labels=short_labels, patch_artist=True, widths=0.6)
    for patch, color in zip(bp["boxes"], PALETTE * 3):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_ylabel("Dose (Gy)")
    ax.set_title("OAR Dose Distribution (All Cases)")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig3_OAR_Dose_BoxPlots.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig3_OAR_Dose_BoxPlots.png")


def fig4_oar_heatmap(oar):
    """Fig 4: OAR constraint compliance heatmap."""
    constraints = {
        "SInte_Dmax": 21.0,
        "Duode_Dmax": 21.0,
        "Colon_Dmax": 30.0,
        "Stom_Dmax": 21.0,
        "Liv-GTV_D700cc": 15.0,
    }

    found_cols = {}
    for key, limit in constraints.items():
        matches = [c for c in oar.columns if key.replace("-", "") in c.replace("-", "").replace(" ", "")]
        if matches:
            found_cols[key] = (matches[0], limit)

    if not found_cols:
        print("  Fig4 — skipped")
        return

    # Build patient x constraint matrix
    patients = oar["case_id"].astype(str).values
    matrix = np.zeros((len(patients), len(found_cols)))
    col_labels = []

    for j, (key, (col, limit)) in enumerate(found_cols.items()):
        vals = pd.to_numeric(oar[col], errors="coerce")
        matrix[:, j] = np.where(vals > limit, 1, np.where(vals.isna(), np.nan, 0))
        col_labels.append(f"{key}\n(<{limit}Gy)")

    fig, ax = plt.subplots(figsize=(8, max(6, len(patients) * 0.25)))
    cmap = plt.cm.colors.ListedColormap(["#2A9D8F", "#E63946"])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", interpolation="nearest", vmin=0, vmax=1)

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=9)
    ax.set_yticks(range(len(patients)))
    ax.set_yticklabels(patients, fontsize=6)
    ax.set_xlabel("OAR Constraint")
    ax.set_ylabel("Case ID")
    ax.set_title("OAR Constraint Compliance (Green=Pass, Red=Exceed)")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig4_OAR_Compliance_Heatmap.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig4_OAR_Compliance_Heatmap.png")


def fig5_toxicity(surv):
    """Fig 5: Toxicity distribution stacked bar."""
    valid = _get_valid_os(surv)
    fig, ax = plt.subplots(figsize=(8, 5))

    groups = ["SCART+IO", "SCART Alone"]
    max_grade = int(valid["tox_grade"].max()) if valid["tox_grade"].notna().any() else 4
    grade_range = range(0, max_grade + 1)
    x = np.arange(len(groups))
    width = 0.5
    bottoms = np.zeros(len(groups))
    colors = ["#2A9D8F", "#E9C46A", "#E76F51", "#E63946", "#8B0000"]

    for g in grade_range:
        heights = []
        for gname in groups:
            gdf = valid[valid["immuno_group"] == gname]
            total = len(gdf)
            cnt = (gdf["tox_grade"] == g).sum()
            heights.append(cnt / total * 100 if total > 0 else 0)
        ax.bar(x, heights, width, bottom=bottoms, label=f"Grade {g}",
               color=colors[g % len(colors)], alpha=0.85)
        bottoms += heights

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Radiation Toxicity Distribution")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 110)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig5_Toxicity_Distribution.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig5_Toxicity_Distribution.png")


def fig6_response(surv):
    """Fig 6: Treatment response distribution."""
    valid = _get_valid_os(surv)
    if "response_local" not in valid.columns:
        print("  Fig6 — skipped (no response data)")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    groups = ["SCART+IO", "SCART Alone"]
    categories = ["CR", "PR", "SD", "PD"]
    colors_resp = ["#2A9D8F", "#457B9D", "#E9C46A", "#E63946"]
    x = np.arange(len(groups))
    width = 0.5
    bottoms = np.zeros(len(groups))

    for cat, color in zip(categories, colors_resp):
        heights = []
        for gname in groups:
            gdf = valid[valid["immuno_group"] == gname]
            total = len(gdf[gdf["response_local"].notna()])
            cnt = (gdf["response_local"] == cat).sum()
            heights.append(cnt / total * 100 if total > 0 else 0)
        ax.bar(x, heights, width, bottom=bottoms, label=cat, color=color, alpha=0.85)
        bottoms += heights

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Local Treatment Response (RECIST)")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 110)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig6_Response_Distribution.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig6_Response_Distribution.png")


def fig7_os_bclc(surv):
    """Fig 7: OS KM by BCLC stage."""
    valid = _get_valid_os(surv)
    fig, ax = plt.subplots(figsize=(8, 6))

    kmfs = []
    for bclc in sorted(valid["bclc"].dropna().unique()):
        gdf = valid[valid["bclc"] == bclc]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        color = COLOR_BCLC.get(bclc, "gray")
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int), label=f"BCLC {bclc} (n={len(gdf)})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)
        kmfs.append(kmf)

    # Multi-group log-rank
    from lifelines.statistics import multivariate_logrank_test
    test_data = valid.dropna(subset=["bclc"])
    if len(test_data["bclc"].unique()) > 1:
        lr = multivariate_logrank_test(test_data["os_months"], test_data["bclc"],
                                        test_data["os_event"].astype(int))
        ax.text(0.98, 0.98, f"Log-rank p = {lr.p_value:.4f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=11, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    if kmfs:
        add_at_risk_counts(*kmfs, ax=ax)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall Survival Probability")
    ax.set_title("Overall Survival by BCLC Stage")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig7_OS_KM_BCLC.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig7_OS_KM_BCLC.png")


def fig8_os_gtv(surv):
    """Fig 8: OS KM by GTV group."""
    valid = _get_valid_os(surv)
    fig, ax = plt.subplots(figsize=(8, 6))

    kmfs = []
    for gname, color in zip(sorted(valid["gtv_group"].dropna().unique()),
                             [COLOR_GTV["small"], COLOR_GTV["large"]]):
        gdf = valid[valid["gtv_group"] == gname]
        if len(gdf) < 2:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(gdf["os_months"], gdf["os_event"].astype(int), label=f"{gname} (n={len(gdf)})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)
        kmfs.append(kmf)

    groups_unique = sorted(valid["gtv_group"].dropna().unique())
    if len(groups_unique) == 2:
        g1 = valid[valid["gtv_group"] == groups_unique[0]]
        g2 = valid[valid["gtv_group"] == groups_unique[1]]
        lr = logrank_test(g1["os_months"], g2["os_months"],
                          g1["os_event"].astype(int), g2["os_event"].astype(int))
        ax.text(0.98, 0.98, f"Log-rank p = {lr.p_value:.4f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=11, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    if kmfs:
        add_at_risk_counts(*kmfs, ax=ax)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall Survival Probability")
    median_gtv = valid["_median_gtv"].iloc[0]
    ax.set_title(f"Overall Survival by GTV Size (median split: {median_gtv:.0f} cm³)")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig8_OS_KM_GTV.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig8_OS_KM_GTV.png")


def fig9_imaging_waterfall(surv, img):
    """Fig 9: Imaging response waterfall plot (all patients)."""
    id_to_immuno = dict(zip(surv["case_id"].astype(str), surv["immuno_group"]))

    records = []
    for _, row in img.iterrows():
        case_id = str(row.get("case_id", ""))
        immuno = id_to_immuno.get(case_id, "Unknown")
        sizes = []
        baseline = None
        for i in range(1, 21):
            size_col = f"尺寸{i:02d}"
            if size_col in img.columns:
                val = pd.to_numeric(row.get(size_col), errors="coerce")
                if pd.notna(val) and val > 0:
                    if baseline is None:
                        baseline = val
                    sizes.append(val)
        if baseline is None or len(sizes) < 2:
            continue
        best = min(sizes[1:])
        pct_best = (best - baseline) / baseline * 100
        records.append({"case_id": case_id, "pct_change": pct_best, "immuno_group": immuno})

    if not records:
        print("  Fig9 — skipped (no imaging data)")
        return

    df = pd.DataFrame(records).sort_values("pct_change")

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [COLOR_IO if r["immuno_group"] == "SCART+IO" else COLOR_ALONE for _, r in df.iterrows()]
    bars = ax.bar(range(len(df)), df["pct_change"], color=colors, width=0.8, alpha=0.85)

    ax.axhline(-30, color="green", linewidth=1, linestyle="--", label="PR threshold (-30%)")
    ax.axhline(20, color="red", linewidth=1, linestyle="--", label="PD threshold (+20%)")
    ax.axhline(0, color="black", linewidth=0.5)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=COLOR_IO, label="SCART+IO"),
                       Patch(facecolor=COLOR_ALONE, label="SCART Alone"),
                       plt.Line2D([0], [0], color="green", linestyle="--", label="PR (-30%)"),
                       plt.Line2D([0], [0], color="red", linestyle="--", label="PD (+20%)")]
    ax.legend(handles=legend_elements, loc="upper left")

    ax.set_xlabel("Patients")
    ax.set_ylabel("Best % Change in Tumor Size")
    ax.set_title("Imaging Response Waterfall Plot")
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig9_Imaging_Waterfall.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig9_Imaging_Waterfall.png")


def fig10_os_bclc_immuno(surv):
    """Fig 10: OS KM for BCLC subgroups stratified by immunotherapy."""
    valid = _get_valid_os(surv)
    bclc_stages = sorted(valid["bclc"].dropna().unique())
    # Only plot stages with enough data
    bclc_stages = [b for b in bclc_stages if len(valid[valid["bclc"] == b]) >= 4]

    if not bclc_stages:
        print("  Fig10 — skipped")
        return

    ncols = min(len(bclc_stages), 3)
    nrows = (len(bclc_stages) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6*ncols, 5*nrows), squeeze=False)

    for idx, bclc in enumerate(bclc_stages):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        sub = valid[valid["bclc"] == bclc]

        for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
            gdf = sub[sub["immuno_group"] == gname]
            if len(gdf) < 2:
                continue
            kmf = KaplanMeierFitter()
            kmf.fit(gdf["os_months"], gdf["os_event"].astype(int),
                    label=f"{gname} (n={len(gdf)})")
            kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)

        ax.set_title(f"BCLC {bclc} (n={len(sub)})")
        ax.set_xlabel("Time (months)")
        ax.set_ylabel("OS Probability")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(loc="lower left", fontsize=8)

    # Hide unused axes
    for idx in range(len(bclc_stages), nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    fig.suptitle("Overall Survival by BCLC Stage — IO vs Alone", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig10_OS_BCLC_Immuno_Subgroups.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig10_OS_BCLC_Immuno_Subgroups.png")


def fig11_waterfall_bclc(surv, img):
    """Fig 11: Waterfall by BCLC stage."""
    id_to_immuno = dict(zip(surv["case_id"].astype(str), surv["immuno_group"]))
    id_to_bclc = dict(zip(surv["case_id"].astype(str), surv["bclc"]))

    records = []
    for _, row in img.iterrows():
        case_id = str(row.get("case_id", ""))
        bclc = id_to_bclc.get(case_id, "Unknown")
        sizes = []
        baseline = None
        for i in range(1, 21):
            size_col = f"尺寸{i:02d}"
            if size_col in img.columns:
                val = pd.to_numeric(row.get(size_col), errors="coerce")
                if pd.notna(val) and val > 0:
                    if baseline is None:
                        baseline = val
                    sizes.append(val)
        if baseline is None or len(sizes) < 2:
            continue
        best = min(sizes[1:])
        pct = (best - baseline) / baseline * 100
        records.append({"case_id": case_id, "pct_change": pct, "bclc": bclc,
                        "immuno_group": id_to_immuno.get(case_id, "Unknown")})

    if not records:
        print("  Fig11 — skipped")
        return

    df = pd.DataFrame(records).sort_values("pct_change")
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [COLOR_BCLC.get(r["bclc"], "gray") for _, r in df.iterrows()]
    ax.bar(range(len(df)), df["pct_change"], color=colors, width=0.8, alpha=0.85)
    ax.axhline(-30, color="green", linewidth=1, linestyle="--")
    ax.axhline(20, color="red", linewidth=1, linestyle="--")
    ax.axhline(0, color="black", linewidth=0.5)

    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=COLOR_BCLC[s], label=f"BCLC {s}") for s in sorted(COLOR_BCLC.keys())]
    ax.legend(handles=legend_elements, loc="upper left")
    ax.set_xlabel("Patients")
    ax.set_ylabel("Best % Change in Tumor Size")
    ax.set_title("Imaging Waterfall by BCLC Stage")
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig11_Waterfall_by_BCLC.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig11_Waterfall_by_BCLC.png")


def fig12_waterfall_gtv(surv, img):
    """Fig 12: Waterfall by GTV group."""
    id_to_immuno = dict(zip(surv["case_id"].astype(str), surv["immuno_group"]))
    id_to_gtv = dict(zip(surv["case_id"].astype(str), surv["gtv_group"]))

    records = []
    for _, row in img.iterrows():
        case_id = str(row.get("case_id", ""))
        gtv_g = id_to_gtv.get(case_id, "Unknown")
        sizes = []
        baseline = None
        for i in range(1, 21):
            size_col = f"尺寸{i:02d}"
            if size_col in img.columns:
                val = pd.to_numeric(row.get(size_col), errors="coerce")
                if pd.notna(val) and val > 0:
                    if baseline is None:
                        baseline = val
                    sizes.append(val)
        if baseline is None or len(sizes) < 2:
            continue
        best = min(sizes[1:])
        pct = (best - baseline) / baseline * 100
        records.append({"case_id": case_id, "pct_change": pct, "gtv_group": gtv_g})

    if not records:
        print("  Fig12 — skipped")
        return

    df = pd.DataFrame(records).sort_values("pct_change")
    fig, ax = plt.subplots(figsize=(10, 6))
    median_gtv = surv["_median_gtv"].iloc[0]
    colors = [COLOR_GTV["small"] if "<=".lower() in r["gtv_group"].lower() else COLOR_GTV["large"]
              for _, r in df.iterrows()]
    ax.bar(range(len(df)), df["pct_change"], color=colors, width=0.8, alpha=0.85)
    ax.axhline(-30, color="green", linewidth=1, linestyle="--")
    ax.axhline(20, color="red", linewidth=1, linestyle="--")
    ax.axhline(0, color="black", linewidth=0.5)

    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=COLOR_GTV["small"], label=f"GTV <= {median_gtv:.0f} cm³"),
                       Patch(facecolor=COLOR_GTV["large"], label=f"GTV > {median_gtv:.0f} cm³")]
    ax.legend(handles=legend_elements, loc="upper left")
    ax.set_xlabel("Patients")
    ax.set_ylabel("Best % Change in Tumor Size")
    ax.set_title("Imaging Waterfall by GTV Size")
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig12_Waterfall_by_GTV.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig12_Waterfall_by_GTV.png")


def fig13_bclc_c_soc(surv):
    """Fig 13: BCLC C — SCART outcomes vs SOC benchmarks."""
    soc_data = [
        ("Atezolizumab+Bev\n(IMbrave150)", 19.2, 27),
        ("Durvalumab+Treme\n(HIMALAYA)", 16.4, 24),
        ("Sorafenib\n(SHARP)", 10.7, 10),
        ("Lenvatinib\n(REFLECT)", 13.6, 24),
    ]

    valid = _get_valid_os(surv)
    bclc_c = valid[valid["bclc"] == "C"]
    io_c = bclc_c[bclc_c["immuno_group"] == "SCART+IO"]
    alone_c = bclc_c[bclc_c["immuno_group"] == "SCART Alone"]

    fig, ax = plt.subplots(figsize=(10, 6))

    # SOC bars
    labels = [d[0] for d in soc_data]
    mos_vals = [d[1] for d in soc_data]

    # Add SCART results
    kmf_io = KaplanMeierFitter()
    if len(io_c) >= 2:
        kmf_io.fit(io_c["os_months"], io_c["os_event"].astype(int))
        io_mos = kmf_io.median_survival_time_
        if np.isfinite(io_mos):
            labels.append(f"SCART+IO\n(this study, n={len(io_c)})")
            mos_vals.append(io_mos)

    kmf_alone = KaplanMeierFitter()
    if len(alone_c) >= 2:
        kmf_alone.fit(alone_c["os_months"], alone_c["os_event"].astype(int))
        alone_mos = kmf_alone.median_survival_time_
        if np.isfinite(alone_mos):
            labels.append(f"SCART Alone\n(this study, n={len(alone_c)})")
            mos_vals.append(alone_mos)

    colors_bar = ["#A8DADC"] * len(soc_data)
    if len(labels) > len(soc_data):
        colors_bar.append(COLOR_IO)
    if len(labels) > len(soc_data) + 1:
        colors_bar.append(COLOR_ALONE)

    bars = ax.barh(range(len(labels)), mos_vals, color=colors_bar, height=0.6, alpha=0.85)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Median Overall Survival (months)")
    ax.set_title("BCLC-C HCC: SCART vs Standard-of-Care Benchmarks")

    for i, v in enumerate(mos_vals):
        ax.text(v + 0.3, i, f"{v:.1f} mo", va="center", fontsize=10)

    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig13_BCLC_C_SOC_Comparison.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig13_BCLC_C_SOC_Comparison.png")


def fig14_confounding(surv):
    """Fig 14: Confounding explanation — DAG-style visualization."""
    valid = _get_valid_os(surv)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    # Panel A: Age distribution
    ax = axes[0]
    for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
        vals = valid[valid["immuno_group"] == gname]["age"].dropna()
        ax.hist(vals, bins=10, alpha=0.6, color=color, label=gname, edgecolor="white")
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Count")
    ax.set_title("Age Distribution")
    ax.legend(fontsize=8)

    # Panel B: GTV distribution
    ax = axes[1]
    for gname, color in [("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]:
        vals = valid[valid["immuno_group"] == gname]["gtv"].dropna()
        ax.hist(vals, bins=10, alpha=0.6, color=color, label=gname, edgecolor="white")
    ax.set_xlabel("GTV (cm³)")
    ax.set_ylabel("Count")
    ax.set_title("GTV Distribution")
    ax.legend(fontsize=8)

    # Panel C: BCLC distribution
    ax = axes[2]
    bclc_stages = sorted(valid["bclc"].dropna().unique())
    x = np.arange(len(bclc_stages))
    width = 0.35
    for i, (gname, color) in enumerate([("SCART+IO", COLOR_IO), ("SCART Alone", COLOR_ALONE)]):
        gdf = valid[valid["immuno_group"] == gname]
        counts = [len(gdf[gdf["bclc"] == s]) for s in bclc_stages]
        ax.bar(x + i*width, counts, width, label=gname, color=color, alpha=0.85)
    ax.set_xticks(x + width/2)
    ax.set_xticklabels([f"BCLC {s}" for s in bclc_stages])
    ax.set_ylabel("Count")
    ax.set_title("BCLC Stage Distribution")
    ax.legend(fontsize=8)

    fig.suptitle("Potential Confounders: IO vs Alone Group Differences", fontsize=14)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig14_Confounding_Explanation.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig14_Confounding_Explanation.png")


def fig15_psm(surv):
    """Fig 15: Propensity score matching balance (love plot)."""
    valid = _get_valid_os(surv)
    covariates = ["age", "gtv", "total_dose", "bed"]
    io = valid[valid["immuno_group"] == "SCART+IO"]
    alone = valid[valid["immuno_group"] == "SCART Alone"]

    smds_before = []
    labels = []
    for cov in covariates:
        a = io[cov].dropna()
        b = alone[cov].dropna()
        if len(a) > 1 and len(b) > 1:
            pooled = np.sqrt(((len(a)-1)*a.std()**2 + (len(b)-1)*b.std()**2) / (len(a)+len(b)-2))
            smd = abs(a.mean() - b.mean()) / pooled if pooled > 0 else 0
            smds_before.append(smd)
            labels.append(cov)

    if not labels:
        print("  Fig15 — skipped")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    y = range(len(labels))
    ax.scatter(smds_before, y, color=COLOR_IO, s=100, zorder=3, label="Before matching")
    ax.axvline(0.1, color="green", linewidth=1, linestyle="--", label="SMD = 0.1 threshold")
    ax.axvline(0.2, color="orange", linewidth=1, linestyle="--", label="SMD = 0.2 threshold")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Absolute Standardized Mean Difference")
    ax.set_title("Covariate Balance (Before Matching)")
    ax.legend(loc="upper right")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig15_PSM_Analysis.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig15_PSM_Analysis.png")


def fig16_io_forest(surv):
    """Fig 16: Forest plot of IO effect (Cox HR) across subgroups."""
    valid = _get_valid_os(surv)

    subgroups = []

    # Overall
    try:
        cph = CoxPHFitter()
        cph.fit(valid[["os_months", "os_event", "immuno_yn"]].dropna().query("os_months > 0"),
                duration_col="os_months", event_col="os_event")
        s = cph.summary.loc["immuno_yn"]
        subgroups.append(("Overall", s["exp(coef)"], s["exp(coef) lower 95%"], s["exp(coef) upper 95%"],
                          len(valid), s["p"]))
    except Exception:
        pass

    # By BCLC
    for bclc in sorted(valid["bclc"].dropna().unique()):
        sub = valid[valid["bclc"] == bclc].dropna(subset=["os_months", "os_event", "immuno_yn"])
        sub = sub[sub["os_months"] > 0]
        if len(sub) < 5 or sub["immuno_yn"].nunique() < 2:
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(sub[["os_months", "os_event", "immuno_yn"]],
                    duration_col="os_months", event_col="os_event")
            s = cph.summary.loc["immuno_yn"]
            subgroups.append((f"BCLC {bclc}", s["exp(coef)"], s["exp(coef) lower 95%"],
                              s["exp(coef) upper 95%"], len(sub), s["p"]))
        except Exception:
            pass

    # By GTV
    for gtv_g in sorted(valid["gtv_group"].dropna().unique()):
        sub = valid[valid["gtv_group"] == gtv_g].dropna(subset=["os_months", "os_event", "immuno_yn"])
        sub = sub[sub["os_months"] > 0]
        if len(sub) < 5 or sub["immuno_yn"].nunique() < 2:
            continue
        try:
            cph = CoxPHFitter()
            cph.fit(sub[["os_months", "os_event", "immuno_yn"]],
                    duration_col="os_months", event_col="os_event")
            s = cph.summary.loc["immuno_yn"]
            subgroups.append((gtv_g, s["exp(coef)"], s["exp(coef) lower 95%"],
                              s["exp(coef) upper 95%"], len(sub), s["p"]))
        except Exception:
            pass

    if not subgroups:
        print("  Fig16 — skipped")
        return

    fig, ax = plt.subplots(figsize=(9, max(4, len(subgroups) * 0.8)))
    labels = [s[0] for s in subgroups]
    hrs = [s[1] for s in subgroups]
    lo = [s[2] for s in subgroups]
    hi = [s[3] for s in subgroups]
    ns = [s[4] for s in subgroups]
    ps = [s[5] for s in subgroups]

    y = range(len(labels))
    ax.errorbar(hrs, y, xerr=[np.array(hrs)-np.array(lo), np.array(hi)-np.array(hrs)],
                fmt="D", color=COLOR_IO, markersize=8, capsize=4, linewidth=2)
    ax.axvline(1, color="black", linewidth=0.8, linestyle="--")

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Hazard Ratio (IO vs Alone)")
    ax.set_title("Immunotherapy Effect on OS — Subgroup Forest Plot")
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())

    for i in range(len(subgroups)):
        ax.text(max(hi) * 1.3, i,
                f"HR={hrs[i]:.2f} [{lo[i]:.2f}-{hi[i]:.2f}]\np={ps[i]:.3f}, n={ns[i]}",
                va="center", fontsize=8)

    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig16_IO_Effect_Forest.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig16_IO_Effect_Forest.png")


# ═══════════════════════════════════════════════════════════════════════════
#  NEW AICE3 FIGURES (Fig17–Fig19)
# ═══════════════════════════════════════════════════════════════════════════

def fig17_aice3_boxplots(surv, aice):
    """Fig 17: AICE3 key metrics box plots by IO group."""
    merged = surv.merge(aice, on="case_id", how="inner", suffixes=("", "_aice"))

    metrics = ["AICE3_raw", "damage_proxy", "H_mean_blood_gy", "E_dyn"]
    titles = ["AICE3 Raw Score", "Damage Proxy", "Mean Blood Dose (Gy)", "E_dynamic"]
    available = [(m, t) for m, t in zip(metrics, titles) if m in merged.columns]

    if not available:
        print("  Fig17 — skipped")
        return

    fig, axes = plt.subplots(1, len(available), figsize=(4*len(available), 5))
    if len(available) == 1:
        axes = [axes]

    for ax, (metric, title) in zip(axes, available):
        io_vals = pd.to_numeric(merged.loc[merged["immuno_group"] == "SCART+IO", metric], errors="coerce").dropna()
        alone_vals = pd.to_numeric(merged.loc[merged["immuno_group"] == "SCART Alone", metric], errors="coerce").dropna()

        bp = ax.boxplot([io_vals, alone_vals], labels=["SCART+IO", "SCART Alone"],
                        patch_artist=True, widths=0.5)
        bp["boxes"][0].set_facecolor(COLOR_IO)
        bp["boxes"][0].set_alpha(0.7)
        bp["boxes"][1].set_facecolor(COLOR_ALONE)
        bp["boxes"][1].set_alpha(0.7)

        if len(io_vals) > 1 and len(alone_vals) > 1:
            _, p = stats.mannwhitneyu(io_vals, alone_vals, alternative="two-sided")
            ax.set_title(f"{title}\np={p:.3f}")
        else:
            ax.set_title(title)

    fig.suptitle("AICE3 Immune-Dose Metrics: IO vs Alone", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig17_AICE3_BoxPlots.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig17_AICE3_BoxPlots.png")


def fig18_aice3_scatter(surv, aice):
    """Fig 18: AICE3 vs OS scatter plots."""
    merged = surv.merge(aice, on="case_id", how="inner", suffixes=("", "_aice"))
    valid = merged.dropna(subset=["os_months", "os_event"]).query("os_months > 0")

    metrics = ["AICE3_raw", "H_mean_blood_gy", "damage_proxy"]
    available = [m for m in metrics if m in valid.columns]

    if not available:
        print("  Fig18 — skipped")
        return

    fig, axes = plt.subplots(1, len(available), figsize=(5*len(available), 5))
    if len(available) == 1:
        axes = [axes]

    for ax, metric in zip(axes, available):
        for gname, color, marker in [("SCART+IO", COLOR_IO, "o"), ("SCART Alone", COLOR_ALONE, "s")]:
            sub = valid[valid["immuno_group"] == gname]
            alive = sub[sub["os_event"] == 0]
            dead = sub[sub["os_event"] == 1]
            ax.scatter(alive[metric], alive["os_months"], c=color, marker=marker,
                       alpha=0.7, s=50, label=f"{gname} (alive)", edgecolors="white")
            ax.scatter(dead[metric], dead["os_months"], c=color, marker="x",
                       alpha=0.7, s=60, label=f"{gname} (dead)")

        ax.set_xlabel(metric)
        ax.set_ylabel("OS (months)")
        ax.set_title(f"{metric} vs Overall Survival")
        ax.legend(fontsize=7, loc="upper right")

    fig.suptitle("AICE3 Metrics vs Survival", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig18_AICE3_vs_OS.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig18_AICE3_vs_OS.png")


def fig19_aice3_correlation(aice):
    """Fig 19: AICE3 metric correlation heatmap."""
    metrics = ["H_mean_blood_gy", "H_body_dyn_gy", "H_liver_dyn_gy", "H_spleen_dyn_gy",
               "E_dyn", "E_static", "AICE3_raw", "damage_proxy"]
    available = [m for m in metrics if m in aice.columns]

    if len(available) < 3:
        print("  Fig19 — skipped")
        return

    corr = aice[available].corr()

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")

    ax.set_xticks(range(len(available)))
    ax.set_xticklabels(available, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(available)))
    ax.set_yticklabels(available, fontsize=9)

    # Annotate
    for i in range(len(available)):
        for j in range(len(available)):
            val = corr.iloc[i, j]
            color = "white" if abs(val) > 0.7 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=8)

    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
    ax.set_title("AICE3 Metric Correlation Matrix")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig19_AICE3_Correlation.png", bbox_inches="tight")
    plt.close(fig)
    print("  Fig19_AICE3_Correlation.png")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Loading data...")
    surv, oar, img, aice = load_data()
    print(f"  Survival: {len(surv)}, OAR: {len(oar)}, Imaging: {len(img)}, AICE3: {len(aice)}")

    print("\nGenerating figures...")

    # V2 figure set (reproduced)
    fig1_os_km(surv)
    fig2_baseline_forest(surv)
    fig3_oar_boxplots(oar)
    fig4_oar_heatmap(oar)
    fig5_toxicity(surv)
    fig6_response(surv)
    fig7_os_bclc(surv)
    fig8_os_gtv(surv)
    fig9_imaging_waterfall(surv, img)
    fig10_os_bclc_immuno(surv)
    fig11_waterfall_bclc(surv, img)
    fig12_waterfall_gtv(surv, img)
    fig13_bclc_c_soc(surv)
    fig14_confounding(surv)
    fig15_psm(surv)
    fig16_io_forest(surv)

    # New AICE3 figures
    fig17_aice3_boxplots(surv, aice)
    fig18_aice3_scatter(surv, aice)
    fig19_aice3_correlation(aice)

    print(f"\nAll figures saved to:\n  {OUT_DIR}")


if __name__ == "__main__":
    main()
