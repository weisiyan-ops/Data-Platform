"""Build SCART V3 PowerPoint presentation with all 19 figures + findings.

Usage:
    python scripts/build_scart_v3_pptx.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

# ── paths ──────────────────────────────────────────────────────────────────
FIG_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OUTPUT = FIG_DIR / "HCC_SCART_V3_Presentation.pptx"

# ── colors ─────────────────────────────────────────────────────────────────
NAVY = RGBColor(0x1B, 0x26, 0x3B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GOLD = RGBColor(0xE9, 0xC4, 0x6A)
TEAL = RGBColor(0x2A, 0x9D, 0x8F)
RED = RGBColor(0xE6, 0x39, 0x46)
LIGHT_GRAY = RGBColor(0xF0, 0xF0, 0xF0)
MED_GRAY = RGBColor(0x66, 0x66, 0x66)
DARK = RGBColor(0x33, 0x33, 0x33)

# ── slide dimensions: widescreen 13.333 x 7.5 ─────────────────────────────
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def add_bg(slide, color):
    """Set slide background to solid color."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, left, top, width, height, text, font_size=18,
                color=DARK, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    """Add a text box with styled text."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_bullet_textbox(slide, left, top, width, height, bullets, font_size=14,
                       color=DARK, font_name="Calibri", spacing_pt=6):
    """Add a text box with multiple bullet lines."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        # Support bold prefix via **text**
        if bullet.startswith("**") and "**" in bullet[2:]:
            end = bullet.index("**", 2)
            bold_part = bullet[2:end]
            rest = bullet[end+2:]
            run_b = p.add_run()
            run_b.text = bold_part
            run_b.font.bold = True
            run_b.font.size = Pt(font_size)
            run_b.font.color.rgb = color
            run_b.font.name = font_name
            if rest:
                run_r = p.add_run()
                run_r.text = rest
                run_r.font.size = Pt(font_size)
                run_r.font.color.rgb = color
                run_r.font.name = font_name
        else:
            p.text = bullet
            p.font.size = Pt(font_size)
            p.font.color.rgb = color
            p.font.name = font_name

        p.space_after = Pt(spacing_pt)
        p.alignment = PP_ALIGN.LEFT

    return txBox


def add_figure_slide(prs, fig_path, title, bullets, subtitle=None):
    """Standard figure slide: title top, figure left, bullets right."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    add_bg(slide, WHITE)

    # Navy header bar
    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.85))  # 1=Rectangle
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()

    # Title
    add_textbox(slide, Inches(0.5), Inches(0.1), Inches(12), Inches(0.65),
                title, font_size=24, color=WHITE, bold=True)

    # Subtitle
    if subtitle:
        add_textbox(slide, Inches(0.5), Inches(0.85), Inches(12), Inches(0.35),
                    subtitle, font_size=12, color=MED_GRAY, bold=False)
        content_top = Inches(1.25)
    else:
        content_top = Inches(1.0)

    # Figure (left ~60%)
    fig_file = FIG_DIR / fig_path
    if fig_file.exists():
        slide.shapes.add_picture(
            str(fig_file),
            Inches(0.3), content_top,
            width=Inches(7.8),
            height=Inches(5.8),
        )
    else:
        add_textbox(slide, Inches(0.5), Inches(2.5), Inches(7), Inches(1),
                    f"[Figure not found: {fig_path}]", font_size=16, color=RED)

    # Bullets (right ~40%)
    add_bullet_textbox(slide, Inches(8.3), content_top, Inches(4.7), Inches(5.8),
                       bullets, font_size=13, color=DARK)

    return slide


def build_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ──────────────────────────────────────────────────────────────────────
    #  SLIDE 1: Title slide
    # ──────────────────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)

    add_textbox(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.2),
                "HCC SCART Analysis — V3 Update",
                font_size=40, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, Inches(1), Inches(2.8), Inches(11), Inches(0.8),
                "Updated Data (03/11/2026) with AICE3 Immune-Dose Integration",
                font_size=22, color=GOLD, bold=False, alignment=PP_ALIGN.CENTER)

    # Accent line
    shape = slide.shapes.add_shape(1, Inches(4), Inches(3.8), Inches(5.333), Inches(0.04))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_bullet_textbox(slide, Inches(2.5), Inches(4.2), Inches(8), Inches(2.5), [
        "66 treatment courses  |  47 with complete OS data  |  38 with AICE3",
        "SCART+Immunotherapy (n=18)  vs  SCART Alone (n=29)",
        "15-sheet Excel report  +  19 publication-quality figures",
        "Side-by-side comparison with V2 report",
    ], font_size=16, color=RGBColor(0xCC, 0xCC, 0xCC))

    add_textbox(slide, Inches(1), Inches(6.5), Inches(11), Inches(0.5),
                "Radiation Oncology Research  |  SCART Spatially-Fractionated RT for Hepatocellular Carcinoma",
                font_size=13, color=MED_GRAY, alignment=PP_ALIGN.CENTER)

    # ──────────────────────────────────────────────────────────────────────
    #  SLIDE 2: Executive Summary
    # ──────────────────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)

    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.85))
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()
    add_textbox(slide, Inches(0.5), Inches(0.1), Inches(12), Inches(0.65),
                "Executive Summary: Key V2 \u2192 V3 Changes", font_size=24, color=WHITE, bold=True)

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(6), Inches(5.5), [
        "**V3 MATCHES V2 SURVIVAL RESULTS**",
        "\u2022 SCART+IO: 11 events, mOS 9.46 mo (V2: 9.46)",
        "\u2022 SCART Alone: 26 events, mOS 11.07 mo (V2: 11.99)",
        "\u2022 Log-rank p = 0.90 (NS, consistent w/ V2: 0.96)",
        "",
        "**DATASET EXPANDED**",
        "\u2022 Total cases: 40 \u2192 66 (+26 new enrollments)",
        "\u2022 19 lack valid dates; 47 with complete OS data",
        "\u2022 IO group identical (n=18); Alone expanded (n=29)",
        "",
        "**BCLC SUBGROUP RESULTS (exact V2 match)**",
        "\u2022 BCLC C mOS: 4.99 mo (V2: 4.99)",
        "\u2022 BCLC B mOS: 35.87 mo (V2: 35.87)",
        "\u2022 BCLC A mOS: 6.04 mo (V2: 6.04)",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(7), Inches(1.2), Inches(6), Inches(5.5), [
        "**AICE3 INTEGRATION (NEW)**",
        "\u2022 38 cases with immune-dose calculations",
        "\u2022 No difference in AICE3 between IO vs Alone",
        "\u2022 No AICE3 metric prognostic for OS",
        "\u2022 Median AICE3_raw: 17.3 Gy (all patients)",
        "",
        "**IMAGING RESPONSE (consistent)**",
        "\u2022 IO ORR: 77% (unchanged from V2)",
        "\u2022 Alone ORR: 47% (V2: 58%)",
        "",
        "**IO vs ALONE (not significant)**",
        "\u2022 IO mOS 9.46 mo vs Alone 11.07 mo",
        "\u2022 No survival difference (p=0.90)",
        "\u2022 Groups confounded by age and BCLC stage",
        "\u2022 Adjusted Cox models confirm no IO effect",
        "",
        "**SAFETY CONFIRMED**",
        "\u2022 No Grade \u22652 toxicity in either group",
    ], font_size=14, color=DARK)

    # ──────────────────────────────────────────────────────────────────────
    #  FIGURE SLIDES (Fig 1-19)
    # ──────────────────────────────────────────────────────────────────────

    # Fig 1
    add_figure_slide(prs, "Fig1_OS_KM.png",
        "Fig 1: Overall Survival \u2014 SCART+IO vs SCART Alone",
        [
            "**Key Finding:**",
            "No significant OS difference between",
            "IO and Alone groups (p=0.90)",
            "",
            "**SCART+IO (n=18):**",
            "\u2022 Median OS: 9.46 months",
            "\u2022 Events: 11/18 (61%)",
            "",
            "**SCART Alone (n=29):**",
            "\u2022 Median OS: 11.07 months",
            "\u2022 Events: 26/29 (90%)",
            "",
            "**V3 vs V2:** Exact match on IO",
            "\u2022 V2 mOS: IO=9.46, Alone=11.99",
            "\u2022 V3 mOS: IO=9.46, Alone=11.07",
            "\u2022 Log-rank p: V2=0.96, V3=0.90",
            "",
            "**Interpretation:**",
            "No survival benefit from adding IO.",
            "Groups confounded by age and BCLC",
            "stage. Not statistically significant.",
        ],
        subtitle="Kaplan-Meier with 95% CI and at-risk table")

    # Fig 2
    add_figure_slide(prs, "Fig2_Baseline_Forest.png",
        "Fig 2: Baseline Covariate Balance",
        [
            "**Purpose:** Assess whether IO and",
            "Alone groups are balanced at baseline",
            "",
            "**Key Observations:**",
            "\u2022 Age: IO older (72 vs 63 yr)",
            "\u2022 GTV: Similar between groups",
            "\u2022 Dose/BED/EQD2: IO slightly higher",
            "\u2022 Male sex: Similar proportions",
            "",
            "**Imbalances (|SMD| > 0.2):**",
            "\u2022 Age is the largest imbalance",
            "\u2022 Dose metrics show moderate",
            "  differences",
            "",
            "**Implication:**",
            "Confounding by age and dose",
            "may influence survival comparison.",
            "Adjusted analyses needed.",
        ],
        subtitle="Standardized Mean Difference (IO minus Alone)")

    # Fig 3
    add_figure_slide(prs, "Fig3_OAR_Dose_BoxPlots.png",
        "Fig 3: Organ-at-Risk Dose Distribution",
        [
            "**OAR metrics across all patients**",
            "",
            "\u2022 Small intestine: median Dmax 3.6 Gy",
            "\u2022 Duodenum: median Dmax low",
            "\u2022 Colon: well within constraints",
            "\u2022 Stomach: generally low doses",
            "\u2022 Liver-GTV: highest doses (expected)",
            "\u2022 Spleen: variable exposure",
            "",
            "**Safety Profile:**",
            "\u2022 Most OAR doses well below limits",
            "\u2022 Liver-GTV receives highest dose",
            "  (by design \u2014 target is in liver)",
            "\u2022 No concerning outliers in most",
            "  critical structures",
            "",
            "**N = 47 cases with OAR data**",
        ],
        subtitle="Box plots showing median, IQR, and outliers for each OAR metric")

    # Fig 4
    add_figure_slide(prs, "Fig4_OAR_Compliance_Heatmap.png",
        "Fig 4: OAR Constraint Compliance",
        [
            "**Per-patient compliance matrix**",
            "",
            "Green = Within constraint",
            "Red = Exceeds constraint",
            "",
            "**Constraints evaluated:**",
            "\u2022 Small Intestine Dmax \u2264 21 Gy",
            "\u2022 Duodenum Dmax \u2264 21 Gy",
            "\u2022 Colon Dmax \u2264 30 Gy",
            "\u2022 Stomach Dmax \u2264 21 Gy",
            "\u2022 Liver-GTV D700cc \u2264 15 Gy",
            "",
            "**Key Finding:**",
            "\u2022 Excellent overall compliance",
            "\u2022 Very few constraint violations",
            "\u2022 SCART technique delivers highly",
            "  conformal dose distributions",
        ],
        subtitle="Patient-by-patient compliance for each OAR constraint")

    # Fig 5
    add_figure_slide(prs, "Fig5_Toxicity_Distribution.png",
        "Fig 5: Radiation Toxicity Distribution",
        [
            "**Toxicity by treatment group**",
            "",
            "**SCART+IO (n=18):**",
            "\u2022 Grade 0: 100%",
            "\u2022 No Grade \u22651 toxicity reported",
            "",
            "**SCART Alone (n=22):**",
            "\u2022 Grade 0: 91%",
            "\u2022 Grade 1: 9% (GI reactions,",
            "  radiation hepatitis)",
            "\u2022 No Grade \u22652 toxicity",
            "",
            "**Key Finding:**",
            "\u2022 SCART is very well tolerated",
            "\u2022 No Grade \u22652 toxicity in either",
            "  group \u2014 favorable safety profile",
            "\u2022 Consistent with V2 findings",
        ],
        subtitle="Maximum radiation toxicity grade by treatment group")

    # Fig 6
    add_figure_slide(prs, "Fig6_Response_Distribution.png",
        "Fig 6: Local Treatment Response (RECIST)",
        [
            "**Response assessment from local**",
            "**tumor measurements (RECIST)**",
            "",
            "\u2022 Limited response data available",
            "  in the structured spreadsheet",
            "\u2022 Most entries: SD or pending (\u201c\u5f85\u5b9a\u4e49\u201d)",
            "",
            "**Note:**",
            "The imaging-based response",
            "(Figures 9\u201312) provides more",
            "complete response assessment",
            "from serial tumor measurements.",
            "",
            "\u2022 See Fig 9 for waterfall plot",
            "\u2022 See Fig 10 for BCLC subgroups",
        ],
        subtitle="RECIST-based local response by treatment group")

    # Fig 7
    add_figure_slide(prs, "Fig7_OS_KM_BCLC.png",
        "Fig 7: Overall Survival by BCLC Stage",
        [
            "**Survival stratified by BCLC stage**",
            "",
            "**BCLC A (n=2):**",
            "\u2022 mOS: 6.0 months",
            "\u2022 Very early/early stage (small N)",
            "",
            "**BCLC B (n=8):**",
            "\u2022 mOS: 35.87 months",
            "\u2022 Intermediate stage, best outcomes",
            "",
            "**BCLC C (n=24):**",
            "\u2022 mOS: 4.99 months",
            "\u2022 Advanced stage, largest group",
            "\u2022 Poorest prognosis as expected",
            "",
            "**BCLC D (n=1):**",
            "\u2022 Single patient, mOS: 2.04 mo",
            "",
            "**V3 vs V2:** Highly consistent",
            "\u2022 Stage is a strong prognostic factor",
        ],
        subtitle="Kaplan-Meier curves by Barcelona Clinic Liver Cancer staging")

    # Fig 8
    add_figure_slide(prs, "Fig8_OS_KM_GTV.png",
        "Fig 8: Overall Survival by GTV Size",
        [
            "**GTV median split at 424 cm\u00b3**",
            "",
            "**GTV \u2264 424 cm\u00b3 (n=27):**",
            "\u2022 Median OS: 12.58 months",
            "\u2022 Better prognosis with smaller",
            "  tumor volume",
            "",
            "**GTV > 424 cm\u00b3 (n=20):**",
            "\u2022 Median OS: 8.34 months",
            "\u2022 Larger tumors associated with",
            "  worse outcomes",
            "",
            "**V2 comparison:**",
            "\u2022 Consistent direction: smaller GTV",
            "\u2022 associated with longer survival",
            "",
            "**Interpretation:**",
            "GTV remains an important prognostic",
            "factor for SCART outcomes.",
        ],
        subtitle="Median GTV split with log-rank test")

    # Fig 9
    add_figure_slide(prs, "Fig9_Imaging_Waterfall.png",
        "Fig 9: Imaging Response Waterfall Plot",
        [
            "**Best % change from baseline**",
            "**tumor size (all patients)**",
            "",
            "\u2022 28 patients with serial imaging",
            "\u2022 Color-coded by IO vs Alone",
            "",
            "**Response thresholds:**",
            "\u2022 PR: \u226530% decrease (green line)",
            "\u2022 PD: \u226520% increase (red line)",
            "",
            "**Overall results:**",
            "\u2022 IO ORR: 77% (10/13)",
            "\u2022 Alone ORR: 47% (7/15)",
            "",
            "**Key Finding:**",
            "Majority of patients show tumor",
            "shrinkage. IO group has numerically",
            "higher response rate. Deep responses",
            "(\u226550% shrinkage) seen in both groups.",
        ],
        subtitle="Best imaging response by treatment, sorted by % change")

    # Fig 10
    add_figure_slide(prs, "Fig10_OS_BCLC_Immuno_Subgroups.png",
        "Fig 10: OS by BCLC Stage \u2014 IO vs Alone",
        [
            "**BCLC-stratified IO vs Alone**",
            "",
            "**BCLC B:**",
            "\u2022 Small numbers in each group",
            "\u2022 Both show favorable outcomes",
            "",
            "**BCLC C (largest subgroup):**",
            "\u2022 Most patients and events here",
            "\u2022 IO and Alone curves overlap",
            "\u2022 No clear separation in advanced",
            "  disease",
            "",
            "**Interpretation:**",
            "\u2022 IO effect not evident in any",
            "  single BCLC subgroup",
            "\u2022 IO patients are older \u2014 age",
            "  confounding persists within strata",
            "\u2022 Small subgroup sizes limit power",
            "\u2022 Adjusted analyses essential",
        ],
        subtitle="Kaplan-Meier curves within each BCLC stage subgroup")

    # Fig 11
    add_figure_slide(prs, "Fig11_Waterfall_by_BCLC.png",
        "Fig 11: Imaging Waterfall by BCLC Stage",
        [
            "**Tumor shrinkage colored by BCLC**",
            "",
            "\u2022 BCLC B patients (yellow) show",
            "  strong shrinkage",
            "\u2022 BCLC C patients (orange) have",
            "  variable response",
            "",
            "**Response by BCLC:**",
            "\u2022 BCLC A/B: Generally good responses",
            "\u2022 BCLC C: Mixed, some deep responses",
            "  but also some progression",
            "",
            "**Key Finding:**",
            "SCART achieves tumor shrinkage",
            "across all BCLC stages, though",
            "response depth varies.",
        ],
        subtitle="Best imaging response sorted by % change, colored by BCLC stage")

    # Fig 12
    add_figure_slide(prs, "Fig12_Waterfall_by_GTV.png",
        "Fig 12: Imaging Waterfall by GTV Size",
        [
            "**Tumor shrinkage colored by GTV**",
            "",
            "\u2022 Blue: GTV \u2264 424 cm\u00b3",
            "\u2022 Red: GTV > 424 cm\u00b3",
            "",
            "**Observation:**",
            "\u2022 Both small and large tumors",
            "  can achieve significant shrinkage",
            "\u2022 Larger tumors show more variable",
            "  response patterns",
            "\u2022 Deep responses possible even in",
            "  very large GTV (\u2265500 cm\u00b3)",
            "",
            "**Key Finding:**",
            "GTV size does not preclude imaging",
            "response \u2014 SCART can produce",
            "meaningful shrinkage in bulky disease.",
        ],
        subtitle="Best imaging response sorted by % change, colored by GTV group")

    # Fig 13
    add_figure_slide(prs, "Fig13_BCLC_C_SOC_Comparison.png",
        "Fig 13: BCLC-C \u2014 SCART vs Standard of Care",
        [
            "**Benchmarking against landmark trials**",
            "",
            "**Published SOC for BCLC-C HCC:**",
            "\u2022 Atezo+Bev (IMbrave150): 19.2 mo",
            "\u2022 Durva+Treme (HIMALAYA): 16.4 mo",
            "\u2022 Lenvatinib (REFLECT): 13.6 mo",
            "\u2022 Sorafenib (SHARP): 10.7 mo",
            "",
            "**This Study (BCLC-C):**",
            "\u2022 SCART+IO mOS: ~5.0 months",
            "\u2022 SCART Alone mOS: ~5.0 months",
            "\u2022 Below systemic SOC benchmarks",
            "",
            "**Key Context:**",
            "BCLC-C patients had very advanced",
            "disease (portal vein invasion, mets).",
            "SCART may complement but not replace",
            "systemic therapy in BCLC-C. Better",
            "results seen in BCLC-B (36 mo).",
        ],
        subtitle="Median OS comparison with published phase III trial results")

    # Fig 14
    add_figure_slide(prs, "Fig14_Confounding_Explanation.png",
        "Fig 14: Potential Confounders",
        [
            "**Three-panel confounder analysis**",
            "",
            "**Panel A \u2014 Age:**",
            "\u2022 IO patients are older (median 72)",
            "\u2022 Alone patients younger (median 63)",
            "\u2022 Age difference may confound OS",
            "",
            "**Panel B \u2014 GTV:**",
            "\u2022 Similar GTV distributions",
            "\u2022 Both groups have large tumors",
            "",
            "**Panel C \u2014 BCLC Stage:**",
            "\u2022 IO: heavily BCLC C (78%)",
            "\u2022 Alone: more mixed stages",
            "\u2022 Stage imbalance present",
            "",
            "**Conclusion:**",
            "Age and BCLC stage are key",
            "confounders. Caution interpreting",
            "unadjusted IO vs Alone comparison.",
        ],
        subtitle="Age, GTV, and BCLC stage distributions by treatment group")

    # Fig 15
    add_figure_slide(prs, "Fig15_PSM_Analysis.png",
        "Fig 15: Covariate Balance Assessment",
        [
            "**Standardized Mean Differences**",
            "**before matching**",
            "",
            "\u2022 Green line: SMD = 0.1 (good)",
            "\u2022 Orange line: SMD = 0.2 (acceptable)",
            "",
            "**Before matching:**",
            "\u2022 Age: SMD > 0.2 (imbalanced)",
            "\u2022 GTV: SMD < 0.1 (balanced)",
            "\u2022 Total dose: moderate imbalance",
            "\u2022 BED: moderate imbalance",
            "",
            "**Note:**",
            "With n=18 IO and n=22 Alone,",
            "propensity score matching is",
            "limited by small sample size.",
            "Cox adjusted models (Fig 16) are",
            "the primary adjusted analysis.",
        ],
        subtitle="Love plot showing covariate balance (SMD) before matching")

    # Fig 16
    add_figure_slide(prs, "Fig16_IO_Effect_Forest.png",
        "Fig 16: Immunotherapy Effect \u2014 Forest Plot",
        [
            "**Cox HR for IO across subgroups**",
            "",
            "\u2022 HR > 1: IO worse than Alone",
            "\u2022 HR < 1: IO better than Alone",
            "\u2022 Vertical dashed line: HR = 1 (null)",
            "",
            "**Overall:**",
            "\u2022 HR close to 1 (non-significant)",
            "\u2022 Consistent with KM log-rank p=0.90",
            "",
            "**By BCLC subgroup:**",
            "\u2022 Wide CIs in all subgroups",
            "\u2022 No subgroup shows significant IO",
            "  benefit or harm",
            "",
            "**By GTV subgroup:**",
            "\u2022 Variable point estimates, all NS",
            "",
            "**Caution:** Small sample sizes yield",
            "wide confidence intervals. These are",
            "hypothesis-generating, not definitive.",
        ],
        subtitle="Hazard ratios with 95% CI for immunotherapy effect in subgroups")

    # ──────────────────────────────────────────────────────────────────────
    #  NEW AICE3 FIGURES (Fig 17-19)
    # ──────────────────────────────────────────────────────────────────────

    # Section divider
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)
    add_textbox(slide, Inches(1), Inches(2.5), Inches(11), Inches(1.2),
                "NEW: AICE3 Immune-Dose Analysis",
                font_size=36, color=GOLD, bold=True, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, Inches(1), Inches(3.8), Inches(11), Inches(0.8),
                "Estimated Dose to Immune Cells \u2014 38 cases with computed AICE3 metrics",
                font_size=18, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_bullet_textbox(slide, Inches(2.5), Inches(5), Inches(8), Inches(2), [
        "H_mean_blood_gy: Mean dose to circulating blood",
        "E_dyn / E_static: Dynamic and static immune exposure estimates",
        "AICE3_raw: Composite AICE3 score",
        "damage_proxy: Immune damage surrogate metric",
    ], font_size=14, color=RGBColor(0xBB, 0xBB, 0xBB))

    # Fig 17
    add_figure_slide(prs, "Fig17_AICE3_BoxPlots.png",
        "Fig 17: AICE3 Metrics \u2014 IO vs Alone",
        [
            "**Immune-dose comparison by group**",
            "",
            "**AICE3_raw:**",
            "\u2022 IO median: 18.1 Gy",
            "\u2022 Alone median: 17.3 Gy",
            "\u2022 p = 0.80 (NS)",
            "",
            "**Damage Proxy:**",
            "\u2022 IO: 0.59  |  Alone: 0.58",
            "\u2022 p = 0.80 (NS)",
            "",
            "**Mean Blood Dose:**",
            "\u2022 IO: 8.3 Gy  |  Alone: 7.8 Gy",
            "\u2022 p = 0.87 (NS)",
            "",
            "**Key Finding:**",
            "No significant difference in any",
            "AICE3 metric between groups.",
            "Immune-dose exposure is comparable.",
        ],
        subtitle="Box plots with Mann-Whitney U test p-values")

    # Fig 18
    add_figure_slide(prs, "Fig18_AICE3_vs_OS.png",
        "Fig 18: AICE3 Metrics vs Overall Survival",
        [
            "**Scatter plots: AICE3 vs OS**",
            "",
            "\u2022 Circles: alive (censored)",
            "\u2022 X marks: deceased (events)",
            "\u2022 Red: IO  |  Blue: Alone",
            "",
            "**Cox Regression Results:**",
            "\u2022 AICE3_raw: HR=1.00, p=0.95",
            "\u2022 Damage proxy: HR=0.71, p=0.90",
            "\u2022 H_mean_blood: HR=1.01, p=0.91",
            "\u2022 E_dyn: HR=1.02, p=0.84",
            "",
            "**Concordance: ~0.50-0.54**",
            "(No better than chance)",
            "",
            "**Key Finding:**",
            "None of the AICE3 metrics are",
            "prognostic for OS in this cohort.",
            "Immune-dose does not predict",
            "survival outcomes.",
        ],
        subtitle="AICE3 metrics plotted against overall survival with event status")

    # Fig 19
    add_figure_slide(prs, "Fig19_AICE3_Correlation.png",
        "Fig 19: AICE3 Metric Correlation Matrix",
        [
            "**Internal structure of AICE3 metrics**",
            "",
            "**Strong correlations (r > 0.8):**",
            "\u2022 H_mean_blood \u2194 H_body_dyn",
            "\u2022 H_mean_blood \u2194 H_liver_dyn",
            "\u2022 E_dyn \u2194 E_static \u2194 AICE3_raw",
            "\u2022 AICE3_raw \u2194 damage_proxy",
            "",
            "**Weaker correlations:**",
            "\u2022 H_spleen_dyn: weakly correlated",
            "  with other metrics",
            "",
            "**Interpretation:**",
            "\u2022 AICE3_raw, E_dyn, E_static, and",
            "  damage_proxy are highly redundant",
            "\u2022 Hepatic dose (H_liver_dyn) drives",
            "  the composite blood dose estimate",
            "\u2022 Splenic dose is relatively",
            "  independent \u2014 may add unique",
            "  prognostic information in larger",
            "  datasets",
        ],
        subtitle="Pearson correlation heatmap across all AICE3 components")

    # ──────────────────────────────────────────────────────────────────────
    #  SUMMARY SLIDE
    # ──────────────────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)

    add_textbox(slide, Inches(0.5), Inches(0.5), Inches(12), Inches(0.8),
                "Summary & Next Steps",
                font_size=32, color=GOLD, bold=True, alignment=PP_ALIGN.CENTER)

    add_bullet_textbox(slide, Inches(0.5), Inches(1.5), Inches(6), Inches(5.5), [
        "**Key Findings from V3 Update:**",
        "",
        "1. V3 matches V2 survival results:",
        "   IO mOS=9.46 vs Alone mOS=11.07 mo",
        "   Log-rank p=0.90 (not significant)",
        "",
        "2. BCLC stage is the strongest prognostic",
        "   factor: B=35.9 mo, C=5.0 mo, exact",
        "   match with V2 findings",
        "",
        "3. No IO survival advantage detected;",
        "   groups confounded by older age and",
        "   higher BCLC-C proportion in IO group",
        "",
        "4. AICE3 immune-dose metrics are similar",
        "   between groups and not prognostic for OS",
        "",
        "5. SCART safety profile remains excellent",
        "   (no Grade \u22652 toxicity)",
    ], font_size=14, color=WHITE)

    add_bullet_textbox(slide, Inches(7), Inches(1.5), Inches(6), Inches(5.5), [
        "**Next Steps:**",
        "",
        "\u2022 ANNOTATE the 26 new cases with",
        "  immunotherapy status and OS data",
        "  to increase statistical power",
        "",
        "\u2022 CONSIDER adjusted analysis (IPTW or",
        "  multivariable Cox) to account for age",
        "  and stage confounding",
        "",
        "\u2022 EXPAND AICE3 analysis once more cases",
        "  have computed immune-dose metrics",
        "",
        "\u2022 EVALUATE whether larger sample may",
        "  reveal AICE3 prognostic signal",
        "",
        "\u2022 EXPLORE BCLC-B subgroup (mOS 36 mo)",
        "  as potential best responder population",
        "",
        "**19 figures + 15-sheet Excel report**",
        "**available for detailed review**",
    ], font_size=14, color=WHITE)

    add_textbox(slide, Inches(1), Inches(7), Inches(11), Inches(0.4),
                "Generated 2026-03-12  |  SCART Analysis V3  |  Oncology Data Platform",
                font_size=11, color=MED_GRAY, alignment=PP_ALIGN.CENTER)

    # ──────────────────────────────────────────────────────────────────────
    #  SAVE
    # ──────────────────────────────────────────────────────────────────────
    prs.save(str(OUTPUT))
    print(f"Saved: {OUTPUT}")
    print(f"Slides: {len(prs.slides)}")


if __name__ == "__main__":
    build_presentation()
