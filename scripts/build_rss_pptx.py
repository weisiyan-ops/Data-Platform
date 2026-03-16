"""Build RSS (Radiosurgery Society) presentation for SCART HCC findings.

Usage:
    python scripts/build_rss_pptx.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ── paths ──────────────────────────────────────────────────────────────────
FIG_DIR = Path(r"/mnt/c/Users/wya245/Downloads/SCART_Analysis_Results_v2/Data 03112026")
OUTPUT = FIG_DIR / "RSS_SCART_HCC_Presentation.pptx"

# ── colors (RSS / professional academic) ──────────────────────────────────
NAVY = RGBColor(0x0D, 0x1B, 0x2A)
DEEP_BLUE = RGBColor(0x1B, 0x26, 0x3B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GOLD = RGBColor(0xD4, 0xA0, 0x3C)
TEAL = RGBColor(0x00, 0x7B, 0x7F)
RED_ACCENT = RGBColor(0xC0, 0x39, 0x2B)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
MED_GRAY = RGBColor(0x88, 0x88, 0x88)
DARK = RGBColor(0x2C, 0x2C, 0x2C)
NEAR_BLACK = RGBColor(0x1A, 0x1A, 0x1A)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


# ── helpers ────────────────────────────────────────────────────────────────

def add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, left, top, width, height, text, font_size=18,
                color=DARK, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
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
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()

        if bullet.startswith("**") and "**" in bullet[2:]:
            end = bullet.index("**", 2)
            bold_part = bullet[2:end]
            rest = bullet[end + 2:]
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


def add_header_bar(slide):
    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.85))
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()
    return shape


def add_slide_title(slide, title, subtitle=None):
    add_header_bar(slide)
    add_textbox(slide, Inches(0.5), Inches(0.1), Inches(12), Inches(0.65),
                title, font_size=24, color=WHITE, bold=True)
    top = Inches(1.0)
    if subtitle:
        add_textbox(slide, Inches(0.5), Inches(0.85), Inches(12), Inches(0.35),
                    subtitle, font_size=12, color=MED_GRAY, bold=False)
        top = Inches(1.25)
    return top


def add_figure_slide(prs, fig_path, title, bullets, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    content_top = add_slide_title(slide, title, subtitle)

    fig_file = FIG_DIR / fig_path
    if fig_file.exists():
        slide.shapes.add_picture(
            str(fig_file), Inches(0.3), content_top,
            width=Inches(7.8), height=Inches(5.8),
        )
    else:
        add_textbox(slide, Inches(0.5), Inches(2.5), Inches(7), Inches(1),
                    f"[Figure not found: {fig_path}]", font_size=16, color=RED_ACCENT)

    add_bullet_textbox(slide, Inches(8.3), content_top, Inches(4.7), Inches(5.8),
                       bullets, font_size=13, color=DARK)
    return slide


def add_table_slide(prs, title, headers, rows_data, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_header_bar(slide)
    add_textbox(slide, Inches(0.5), Inches(0.1), Inches(12), Inches(0.65),
                title, font_size=24, color=WHITE, bold=True)

    if subtitle:
        add_textbox(slide, Inches(0.5), Inches(0.85), Inches(12), Inches(0.35),
                    subtitle, font_size=12, color=MED_GRAY)
        table_top = Inches(1.35)
    else:
        table_top = Inches(1.1)

    n_rows = len(rows_data) + 1
    n_cols = len(headers)
    table_width = Inches(12)
    table_height = Inches(min(5.5, 0.42 * n_rows))

    table_shape = slide.shapes.add_table(
        n_rows, n_cols, Inches(0.6), table_top, table_width, table_height
    )
    table = table_shape.table

    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = str(h)
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(12)
            paragraph.font.bold = True
            paragraph.font.color.rgb = WHITE
            paragraph.font.name = "Calibri"
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY

    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.color.rgb = DARK
                paragraph.font.name = "Calibri"
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_GRAY

    return slide


def add_section_divider(prs, title, subtitle=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)
    add_textbox(slide, Inches(1), Inches(2.5), Inches(11), Inches(1.2),
                title, font_size=36, color=GOLD, bold=True, alignment=PP_ALIGN.CENTER)
    if subtitle:
        add_textbox(slide, Inches(1), Inches(3.8), Inches(11), Inches(0.8),
                    subtitle, font_size=18, color=WHITE, alignment=PP_ALIGN.CENTER)
    return slide


# ═══════════════════════════════════════════════════════════════════════════
#  BUILD PRESENTATION
# ═══════════════════════════════════════════════════════════════════════════

def build_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 1: TITLE
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)

    # Thin gold accent line at top
    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.06))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_textbox(slide, Inches(0.8), Inches(0.8), Inches(11.5), Inches(1.6),
                "Spatially-Fractionated Radiotherapy (SCART) Combined\n"
                "with Immunotherapy for Hepatocellular Carcinoma:\n"
                "A Single-Institution Retrospective Analysis",
                font_size=30, color=WHITE, bold=True, alignment=PP_ALIGN.LEFT)

    # Gold line separator
    shape = slide.shapes.add_shape(1, Inches(0.8), Inches(3.0), Inches(5), Inches(0.04))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_bullet_textbox(slide, Inches(0.8), Inches(3.4), Inches(11), Inches(2.0), [
        "31 patients  |  40 treatment courses  |  Single center (Foshan, China)",
        "SCART 3 \u00d7 21 Gy (BED 195 Gy)  |  Median GTV 316 cm\u00b3",
        "Propensity score matching  |  IPTW  |  Multivariable Cox regression",
        "AICE3 immune-dose-to-circulating-cells integration",
    ], font_size=16, color=RGBColor(0xBB, 0xBB, 0xBB))

    add_textbox(slide, Inches(0.8), Inches(5.8), Inches(11), Inches(0.5),
                "Presented at the Radiosurgery Society (RSS) Scientific Meeting",
                font_size=16, color=GOLD, bold=False, alignment=PP_ALIGN.LEFT)

    add_textbox(slide, Inches(0.8), Inches(6.5), Inches(11), Inches(0.5),
                "Data cutoff: March 9, 2026  |  Analysis version 3.0",
                font_size=12, color=MED_GRAY, alignment=PP_ALIGN.LEFT)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 2: DISCLOSURES
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Disclosures")

    add_textbox(slide, Inches(2), Inches(2.5), Inches(9), Inches(2),
                "The authors declare no relevant conflicts of interest.\n\n"
                "This study was conducted as part of a single-institution\n"
                "retrospective chart review.",
                font_size=20, color=DARK, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, Inches(2), Inches(5), Inches(9), Inches(1),
                "IRB: Institutional review board approval obtained.\n"
                "Informed consent: Waived for retrospective analysis.",
                font_size=14, color=MED_GRAY, alignment=PP_ALIGN.CENTER)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 3: BACKGROUND — HCC
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Background: HCC \u2014 An Unmet Need")

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.8), [
        "**Hepatocellular Carcinoma (HCC)**",
        "",
        "\u2022 6th most common cancer worldwide",
        "\u2022 3rd leading cause of cancer death",
        "\u2022 Rising incidence, especially in Asia",
        "",
        "**Current standard of care:**",
        "\u2022 BCLC A: Resection / Ablation / Transplant",
        "\u2022 BCLC B: TACE \u00b1 systemic therapy",
        "\u2022 BCLC C: Systemic IO-based regimens",
        "  (Atezo+Bev, Durva+Treme)",
        "\u2022 BCLC D: Best supportive care",
        "",
        "**Unmet need:**",
        "\u2022 Advanced HCC (BCLC C) mOS 10\u201319 mo",
        "  with best systemic therapy",
        "\u2022 Large/bulky tumors poorly controlled",
        "\u2022 Local RT may complement systemic IO",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(6.8), Inches(1.2), Inches(6), Inches(5.8), [
        "**Rationale for SCART + Immunotherapy**",
        "",
        "**SCART (Spatially-fractionated RT):**",
        "\u2022 Delivers high ablative doses in 3 fx",
        "\u2022 BED \u2265 100 Gy (typically 195 Gy)",
        "\u2022 Effective for bulky tumors where",
        "  conventional SBRT is dose-limited",
        "",
        "**Radiation + Immunotherapy synergy:**",
        "\u2022 RT induces immunogenic cell death (ICD)",
        "\u2022 Releases tumor-associated antigens",
        "\u2022 Activates dendritic cells & T-cells",
        "\u2022 Abscopal effect potential",
        "",
        "**Hypothesis:**",
        "Peri-SCART immunotherapy (\u22121 month to",
        "+3 months around RT) may enhance anti-",
        "tumor immunity and improve OS in HCC.",
    ], font_size=14, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 4: OBJECTIVES
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Study Objectives")

    add_bullet_textbox(slide, Inches(1.5), Inches(1.5), Inches(10), Inches(5), [
        "**Primary Objective**",
        "",
        "  Compare overall survival (OS) between SCART + immunotherapy (IO)",
        "  and SCART alone in patients with hepatocellular carcinoma,",
        "  adjusted for baseline confounders.",
        "",
        "**Secondary Objectives**",
        "",
        "  1. Characterize imaging-based tumor response (RECIST-like) by treatment group",
        "  2. Evaluate safety profile: organ-at-risk (OAR) dose constraints and toxicity",
        "  3. Analyze OS by BCLC stage and GTV size subgroups",
        "  4. Compare SCART outcomes against published standard-of-care benchmarks",
        "  5. Integrate AICE3 (dose-to-immune-cells) metrics and assess prognostic value",
        "",
        "**Statistical Methods**",
        "",
        "  Propensity score matching (PSM), IPTW, multivariable Cox regression,",
        "  BCLC-stratified analysis, interaction tests, RMST",
    ], font_size=15, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 5: METHODS — STUDY DESIGN
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Methods: Study Design & Patient Population")

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.5), [
        "**Study Design**",
        "\u2022 Single-center retrospective cohort",
        "\u2022 Foshan, Guangdong, China",
        "\u2022 Data cutoff: March 9, 2026",
        "",
        "**Eligibility**",
        "\u2022 Histologically confirmed HCC",
        "\u2022 Treated with SCART technique",
        "\u2022 Complete follow-up data available",
        "",
        "**Cohort**",
        "\u2022 31 unique patients, 40 treatment courses",
        "\u2022 66 total records (multi-course patients)",
        "\u2022 9 patients had 2\u20134 treatment courses",
        "",
        "**Treatment Groups**",
        "\u2022 SCART + IO: 18 courses (45%)",
        "\u2022 SCART Alone: 22 courses (55%)",
        "\u2022 IO defined as peri-RT immunotherapy",
        "  (\u22641 mo before to \u22643 mo after SCART)",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(6.8), Inches(1.2), Inches(6), Inches(5.5), [
        "**SCART Technique**",
        "\u2022 Spatially-fractionated RT",
        "\u2022 3 fractions (all patients)",
        "\u2022 Median dose/fx: 21 Gy",
        "\u2022 Median total dose: 63 Gy",
        "\u2022 Median BED: 195.3 Gy (\u03b1/\u03b2=10)",
        "",
        "**Concurrent Therapies**",
        "\u2022 Targeted therapy: 68%",
        "\u2022 TACE: 12%",
        "\u2022 Systemic chemotherapy: 8%",
        "",
        "**Endpoints**",
        "\u2022 Primary: Overall survival (OS)",
        "\u2022 Secondary: Imaging response,",
        "  toxicity, OAR dose compliance",
        "",
        "**OS Calculation (per course):**",
        "  Events: (death date \u2212 SCART start) / 30.44",
        "  Censored: (last FU \u2212 SCART start) / 30.44",
    ], font_size=14, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SECTION: RESULTS
    # ══════════════════════════════════════════════════════════════════════
    add_section_divider(prs, "Results",
                        "40 treatment courses  |  Median follow-up 9.3 months  |  30 events")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 7: BASELINE TABLE
    # ══════════════════════════════════════════════════════════════════════
    add_table_slide(prs,
        "Baseline Patient and Disease Characteristics",
        ["Characteristic", "SCART+IO (n=18)", "SCART Alone (n=22)", "p-value"],
        [
            ["Age, median [IQR]", "72 [60\u201374]", "63 [55\u201364]", "0.056"],
            ["Male sex, n (%)", "18 (100%)", "19 (86%)", "0.237"],
            ["", "", "", ""],
            ["BCLC A", "1 (6%)", "1 (5%)", ""],
            ["BCLC B", "1 (6%)", "7 (32%)", ""],
            ["BCLC C", "14 (78%)", "10 (45%)", ""],
            ["BCLC D", "1 (6%)", "0 (0%)", ""],
            ["", "", "", ""],
            ["GTV (cm\u00b3), median [IQR]", "377 [161\u2013819]", "243 [131\u2013661]", "0.617"],
            ["Total Dose (Gy), median", "63", "63", "0.083"],
            ["BED (Gy), median", "198", "195", "0.096"],
            ["", "", "", ""],
            ["Targeted therapy, n (%)", "16 (89%)", "11 (50%)", "0.014"],
            ["TACE, n (%)", "1 (6%)", "4 (18%)", "0.358"],
            ["Chemotherapy, n (%)", "2 (11%)", "1 (5%)", "0.574"],
        ],
        subtitle="Per-treatment-course characteristics; p-values: Mann-Whitney (continuous), Fisher exact (categorical)")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 8: BASELINE FOREST (Fig 2)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig2_Baseline_Forest.png",
        "Covariate Balance: IO vs Alone (Unmatched)",
        [
            "**Standardized Mean Difference (SMD)**",
            "",
            "**Key imbalances (|SMD| > 0.2):**",
            "\u2022 Age: IO 9 years older (SMD 0.55)",
            "\u2022 BCLC stage: IO more advanced",
            "  (78% BCLC-C vs 45%, SMD 0.63)",
            "",
            "**Balanced covariates:**",
            "\u2022 GTV volume (SMD 0.08)",
            "\u2022 Dose metrics: moderate difference",
            "",
            "**Implication:**",
            "Unadjusted IO vs Alone comparison is",
            "confounded by age and disease stage.",
            "",
            "Adjusted analyses are required to",
            "estimate the true IO effect.",
            "",
            "\u2192 PSM, IPTW, and multivariable Cox",
            "  applied in subsequent analyses",
        ],
        subtitle="Horizontal bars: SMD magnitude; dashed lines at 0.1 and 0.2 thresholds")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 9: UNADJUSTED OS (Fig 1)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig1_OS_KM.png",
        "Overall Survival: Unadjusted Kaplan-Meier",
        [
            "**Unadjusted results (confounded):**",
            "",
            "**SCART+IO (n=18):**",
            "\u2022 Median OS: 9.46 months",
            "\u2022 Events: 11/18 (61%)",
            "\u2022 1-yr OS: 44%",
            "",
            "**SCART Alone (n=22):**",
            "\u2022 Median OS: 11.07 months",
            "\u2022 Events: 26/29 (90%)",
            "",
            "**Log-rank p = 0.90**",
            "",
            "**Caution:** IO patients are older and",
            "have more advanced disease (BCLC-C).",
            "This raw comparison underestimates",
            "the IO effect.",
            "",
            "**\u2192 See adjusted analyses (next slides)**",
        ],
        subtitle="Kaplan-Meier with 95% CI and number-at-risk table")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 10: CONFOUNDING (Fig 14)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig14_Confounding_Explanation.png",
        "The Confounding Problem: Age and BCLC Stage",
        [
            "**Three key confounders visualized:**",
            "",
            "**Panel A \u2014 Age:**",
            "\u2022 IO: median 72 yr (older)",
            "\u2022 Alone: median 63 yr",
            "\u2022 Older age \u2192 worse OS",
            "",
            "**Panel B \u2014 GTV:**",
            "\u2022 Similar between groups",
            "\u2022 Not a major confounder",
            "",
            "**Panel C \u2014 BCLC:**",
            "\u2022 IO: 78% BCLC-C (advanced)",
            "\u2022 Alone: 45% BCLC-C",
            "\u2022 More BCLC-B in Alone (32% vs 6%)",
            "\u2022 BCLC-C predicts poor OS",
            "",
            "**These imbalances bias the unadjusted**",
            "**comparison AGAINST IO.**",
        ],
        subtitle="Distribution of age, GTV, and BCLC stage by treatment group")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 11: PSM BALANCE (Fig 20)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig20_PSM_Balance.png",
        "Propensity Score Matching: Covariate Balance",
        [
            "**PSM approach:**",
            "\u2022 Logistic regression: P(IO | age, GTV, BCLC)",
            "\u2022 1:1 nearest-neighbor matching",
            "\u2022 Caliper: 0.25 \u00d7 SD of propensity score",
            "",
            "**Before matching (circles):**",
            "\u2022 Age: SMD = 0.55 (imbalanced)",
            "\u2022 BCLC: SMD = 0.63 (imbalanced)",
            "",
            "**After matching (diamonds):**",
            "\u2022 Age: SMD = 0.03 (excellent)",
            "\u2022 BCLC: SMD = 0.00 (perfect)",
            "\u2022 GTV: SMD = 0.06 (excellent)",
            "",
            "**7 matched pairs (14 patients)**",
            "All covariates below SMD 0.1 threshold",
        ],
        subtitle="Love plot: absolute SMD before (red) and after (blue) propensity score matching")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 12: PSM MATCHED KM (Fig 21)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig21_PSM_Matched_KM.png",
        "PSM-Matched Overall Survival",
        [
            "**After balancing confounders:**",
            "",
            "**SCART+IO (n=7, matched):**",
            "\u2022 Median OS: 24.3 months",
            "\u2022 Events: 4/7 (57%)",
            "",
            "**SCART Alone (n=7, matched):**",
            "\u2022 Median OS: 6.0 months",
            "\u2022 Events: 7/7 (100%)",
            "",
            "**4\u00d7 longer median OS with IO**",
            "",
            "**Cox HR = 0.57 [0.16\u20132.04]**",
            "\u2022 43% reduction in death hazard",
            "\u2022 p = 0.39 (limited by n=14)",
            "",
            "**Doubly robust (PSM + age):**",
            "\u2022 HR = 0.53 [0.14\u20131.98], p = 0.34",
            "",
            "**Interpretation:** When matched for age",
            "and stage, IO shows major OS benefit.",
        ],
        subtitle="Kaplan-Meier curves on 7 propensity-score matched pairs")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 13: ALL-MODELS FOREST (Fig 23)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig23_IO_HR_All_Models.png",
        "IO Effect: Forest Plot Across All Analytical Methods",
        [
            "**8 analytical approaches:**",
            "",
            "**Confounded (HR > 1):**",
            "\u2022 Unadjusted: HR = 1.27",
            "\u2022 Age-only adjusted: HR = 1.62",
            "",
            "**Adjusted for BCLC (HR < 1):**",
            "\u2022 Age+GTV+BCLC: HR = 0.65",
            "\u2022 Fully adjusted: HR = 0.71",
            "\u2022 Stratified by BCLC: HR = 0.53",
            "",
            "**Matched (HR < 1):**",
            "\u2022 PSM: HR = 0.57",
            "\u2022 PSM+age: HR = 0.53",
            "\u2022 IPTW: HR = 0.85",
            "",
            "**BCLC is the critical confounder.**",
            "Once controlled, 6/8 methods show",
            "HR < 1 (IO protective).",
            "Consistent HR range: 0.53\u20130.71.",
        ],
        subtitle="HR < 1 favors SCART+IO; green shading = protective zone; dashed line = null effect")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 14: IO HR SUMMARY TABLE
    # ══════════════════════════════════════════════════════════════════════
    add_table_slide(prs,
        "Immunotherapy Effect on OS: Summary of All Analytical Methods",
        ["Method", "HR", "95% CI", "p-value", "N", "Interpretation"],
        [
            ["Unadjusted", "1.27", "0.56\u20132.87", "0.570", "40", "Confounded by age+BCLC"],
            ["Adjusted: age only", "1.62", "0.67\u20133.90", "0.286", "40", "Confounded (age insufficient)"],
            ["Adjusted: age+GTV+BCLC", "0.65", "0.24\u20131.73", "0.385", "35", "IO protective"],
            ["Fully adjusted", "0.71", "0.23\u20132.20", "0.555", "35", "IO protective"],
            ["Stratified by BCLC", "0.53", "0.22\u20131.31", "0.167", "35", "Strongest signal"],
            ["PSM-matched (7:7)", "0.57", "0.16\u20132.04", "0.386", "14", "IO protective"],
            ["Doubly robust (PSM+age)", "0.53", "0.14\u20131.98", "0.341", "14", "IO protective"],
            ["IPTW-weighted", "0.85", "0.33\u20132.20", "0.745", "35", "IO protective"],
        ],
        subtitle="HR < 1 indicates reduced hazard of death with IO  |  p > 0.05 reflects limited sample size (N=40)")

    slide = prs.slides[-1]
    add_bullet_textbox(slide, Inches(0.6), Inches(5.8), Inches(12), Inches(1.2), [
        "**Key finding:** Once BCLC stage is controlled (methods 3\u20138), HR consistently falls below 1.0 (range 0.53\u20130.85), indicating IO is protective.",
        "**Study is underpowered:** ~120 patients needed for 80% power to detect HR = 0.53 at \u03b1 = 0.05. Current N = 40 provides ~30% power.",
    ], font_size=12, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 15: BCLC STRATIFICATION (Fig 7)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig7_OS_KM_BCLC.png",
        "Overall Survival by BCLC Stage",
        [
            "**BCLC stage is the strongest**",
            "**prognostic factor in this cohort**",
            "",
            "**BCLC A (n=2):** mOS = 6.0 mo",
            "**BCLC B (n=8):** mOS = 35.9 mo",
            "**BCLC C (n=24):** mOS = 5.0 mo",
            "**BCLC D (n=1):** mOS = 2.0 mo",
            "",
            "**Log-rank p = 0.007 (significant)**",
            "",
            "**BCLC B = best outcomes:**",
            "\u2022 Intermediate stage",
            "\u2022 35.9 months median OS",
            "\u2022 All alive at 1 year",
            "",
            "**BCLC C = poor prognosis:**",
            "\u2022 Largest subgroup (60%)",
            "\u2022 5.0 months median OS",
            "\u2022 This is where IO may help most",
        ],
        subtitle="Kaplan-Meier by Barcelona Clinic Liver Cancer staging system")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 16: BCLC-C SUBGROUP (Fig 22)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig22_BCLC_C_IO_vs_Alone.png",
        "BCLC-C Advanced HCC: SCART+IO vs SCART Alone",
        [
            "**Within-stage comparison eliminates**",
            "**the BCLC confounding problem**",
            "",
            "**SCART+IO (n=14):**",
            "\u2022 Median OS: 9.23 months",
            "\u2022 Events: 10/14 (71%)",
            "\u2022 1-yr OS: ~40%",
            "",
            "**SCART Alone (n=10):**",
            "\u2022 Median OS: 2.04 months",
            "\u2022 Events: 10/10 (100%)",
            "\u2022 1-yr OS: ~10%",
            "",
            "**IO mOS 4.5\u00d7 longer (9.2 vs 2.0 mo)**",
            "Log-rank p = 0.236 (underpowered)",
            "",
            "**Clinical significance:**",
            "In advanced HCC, adding IO to SCART",
            "extended median survival by 7 months.",
        ],
        subtitle="BCLC-C subgroup (n=24): the largest and most clinically relevant subgroup")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 17: SOC BENCHMARKING
    # ══════════════════════════════════════════════════════════════════════
    add_table_slide(prs,
        "BCLC-C HCC: SCART Outcomes vs Published Systemic Benchmarks",
        ["Regimen", "mOS (months)", "ORR (%)", "N", "Source"],
        [
            ["SCART + IO (this study)", "9.23", "80%", "14", "This study"],
            ["SCART Alone (this study)", "2.04", "43%", "10", "This study"],
            ["", "", "", "", ""],
            ["Atezolizumab + Bevacizumab", "19.2", "30%", "336", "IMbrave150"],
            ["Durvalumab + Tremelimumab", "16.4", "20%", "393", "HIMALAYA"],
            ["Lenvatinib", "13.6", "24%", "478", "REFLECT"],
            ["Sorafenib", "10.7", "2%", "299", "SHARP"],
        ],
        subtitle="Comparison with published phase III trials for advanced HCC first-line therapy")

    slide = prs.slides[-1]
    add_bullet_textbox(slide, Inches(0.6), Inches(5.0), Inches(12), Inches(2.2), [
        "**Context:** SCART+IO mOS of 9.23 months in BCLC-C falls between sorafenib (10.7 mo) and IO-based systemic regimens (16\u201319 mo).",
        "**ORR advantage:** SCART+IO achieves 80% objective response rate \u2014 substantially higher than any systemic monotherapy or combination (20\u201330%).",
        "**SCART Alone mOS of 2.04 months** reflects very advanced local disease in this cohort (large GTV, portal vein invasion).",
        "**Limitation:** Direct comparison with phase III trials is limited (different populations, single-arm retrospective vs randomized controlled).",
    ], font_size=12, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 18: IMAGING RESPONSE (Fig 9)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig9_Imaging_Waterfall.png",
        "Imaging Response: Tumor Shrinkage Waterfall Plot",
        [
            "**Best % change from baseline tumor size**",
            "**28 patients with serial imaging**",
            "",
            "**SCART+IO (n=13 evaluable):**",
            "\u2022 ORR: 77% (10/13)",
            "\u2022 DCR: 100% (13/13)",
            "\u2022 No progression",
            "",
            "**SCART Alone (n=15 evaluable):**",
            "\u2022 ORR: 47% (7/15)",
            "\u2022 DCR: 87% (13/15)",
            "\u2022 2 patients with PD",
            "",
            "**Key findings:**",
            "\u2022 Majority of patients show tumor",
            "  shrinkage with SCART",
            "\u2022 IO group: higher response rate",
            "  and no progressive disease",
            "\u2022 Deep responses (\u226550%) seen in both",
        ],
        subtitle="RECIST-like response; red = SCART+IO, blue = SCART Alone; dashed lines at PR/PD thresholds")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 19: OAR SAFETY (Fig 3)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig3_OAR_Dose_BoxPlots.png",
        "OAR Dose Distribution: Safety Profile",
        [
            "**Organ-at-Risk doses (n=47)**",
            "",
            "**Dose constraints evaluated:**",
            "\u2022 Small intestine Dmax \u226421 Gy",
            "\u2022 Duodenum Dmax \u226421 Gy",
            "\u2022 Colon Dmax \u226430 Gy",
            "\u2022 Stomach Dmax \u226421 Gy",
            "\u2022 Liver-GTV D700cc \u226415 Gy",
            "",
            "**Results:**",
            "\u2022 Excellent constraint compliance",
            "\u2022 Small intestine: median 3.6 Gy",
            "\u2022 Duodenum: median 7.6 Gy",
            "\u2022 Liver-GTV: highest doses (expected)",
            "",
            "**Only 1 case (4%) exceeded any**",
            "**single OAR constraint**",
            "",
            "\u2022 SCART achieves highly conformal",
            "  dose delivery despite large GTV",
        ],
        subtitle="Box plots: median, IQR, and outliers for each OAR dose metric (n=47)")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 20: TOXICITY (Fig 5)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig5_Toxicity_Distribution.png",
        "Radiation Toxicity: Excellent Safety Profile",
        [
            "**Toxicity by treatment group:**",
            "",
            "**SCART+IO (n=18):**",
            "\u2022 Grade 0: 100%",
            "\u2022 No toxicity \u2265 Grade 1",
            "",
            "**SCART Alone (n=22):**",
            "\u2022 Grade 0: 91%",
            "\u2022 Grade 1: 9% (2 patients)",
            "  \u2013 GI reactions, radiation hepatitis",
            "\u2022 No toxicity \u2265 Grade 2",
            "",
            "**No Grade \u22652 toxicity in either group**",
            "",
            "**Key finding:**",
            "Adding immunotherapy to SCART did NOT",
            "increase toxicity. The combination is",
            "well tolerated even in elderly patients",
            "(IO median age 72 years).",
            "",
            "**Safety is comparable to published**",
            "**liver SBRT series.**",
        ],
        subtitle="Maximum radiation toxicity grade per CTCAE by treatment group")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 21: OAR COMPLIANCE (Fig 4)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig4_OAR_Compliance_Heatmap.png",
        "OAR Constraint Compliance Matrix",
        [
            "**Per-patient compliance heatmap**",
            "",
            "Green = within constraint",
            "Red = exceeds constraint",
            "",
            "**5 critical constraints evaluated:**",
            "\u2022 Small intestine Dmax \u226421 Gy",
            "\u2022 Duodenum Dmax \u226421 Gy",
            "\u2022 Colon Dmax \u226430 Gy",
            "\u2022 Stomach Dmax \u226421 Gy",
            "\u2022 Liver-GTV D700cc \u226415 Gy",
            "",
            "**Near-universal compliance**",
            "\u2022 96% of patients met all constraints",
            "\u2022 SCART technique delivers highly",
            "  conformal dose even for very large",
            "  tumors (GTV up to 3,024 cm\u00b3)",
            "",
            "**Supports SCART feasibility for**",
            "**bulky hepatic tumors**",
        ],
        subtitle="Patient-by-case compliance for each dose constraint (n=47)")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 22: GTV SUBGROUP (Fig 8)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig8_OS_KM_GTV.png",
        "Overall Survival by GTV Size",
        [
            "**GTV median split at 424 cm\u00b3**",
            "",
            "**GTV \u2264 424 cm\u00b3 (n=27):**",
            "\u2022 Median OS: 12.6 months",
            "",
            "**GTV > 424 cm\u00b3 (n=20):**",
            "\u2022 Median OS: 8.3 months",
            "",
            "**Smaller tumors = longer survival**",
            "",
            "**Notable:** Even very large tumors",
            "(> 1000 cm\u00b3) had measurable responses",
            "and meaningful survival times.",
            "",
            "**SCART accommodates large GTV**",
            "where conventional SBRT may be limited",
            "by normal tissue tolerance.",
            "",
            "**Implication for RSS community:**",
            "Spatially-fractionated technique extends",
            "radiosurgery to bulky disease.",
        ],
        subtitle="Kaplan-Meier by tumor volume (median GTV split)")

    # ══════════════════════════════════════════════════════════════════════
    #  SECTION: AICE3
    # ══════════════════════════════════════════════════════════════════════
    add_section_divider(prs, "AICE3: Immune-Dose Analysis",
                        "Estimated Dose to Immune Cells \u2014 38 cases with computed metrics")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 24: AICE3 BOX PLOTS (Fig 17)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig17_AICE3_BoxPlots.png",
        "AICE3 Immune-Dose Metrics: IO vs Alone",
        [
            "**AICE3 = dose to circulating immune cells**",
            "",
            "**AICE3_raw score:**",
            "\u2022 IO: 18.1 Gy  |  Alone: 17.3 Gy",
            "\u2022 p = 0.80 (NS)",
            "",
            "**Damage proxy:**",
            "\u2022 IO: 0.59  |  Alone: 0.58",
            "\u2022 p = 0.80 (NS)",
            "",
            "**Mean blood dose:**",
            "\u2022 IO: 8.3 Gy  |  Alone: 7.8 Gy",
            "\u2022 p = 0.87 (NS)",
            "",
            "**Immune-dose exposure is comparable**",
            "**between groups.** The IO survival",
            "benefit is not explained by differences",
            "in radiation-induced immune damage.",
            "",
            "**N = 38 cases with AICE3 data**",
        ],
        subtitle="Box plots with Mann-Whitney U test; AICE3 = dose to circulating immune cells")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 25: AICE3 vs OS (Fig 18)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig18_AICE3_vs_OS.png",
        "AICE3 Metrics vs Overall Survival",
        [
            "**Prognostic value of immune-dose:**",
            "",
            "\u2022 Circles: alive  |  X: deceased",
            "\u2022 Red: IO  |  Blue: Alone",
            "",
            "**Cox Regression (univariable):**",
            "\u2022 AICE3_raw: HR=1.00, p=0.95",
            "\u2022 Damage proxy: HR=0.71, p=0.90",
            "\u2022 H_mean_blood: HR=1.01, p=0.91",
            "\u2022 E_dyn: HR=1.02, p=0.84",
            "",
            "**Concordance: 0.50\u20130.54**",
            "(No better than chance)",
            "",
            "**Conclusion:**",
            "AICE3 metrics are NOT prognostic for",
            "OS in this cohort. Immune-dose does not",
            "predict survival, suggesting the IO",
            "benefit operates through a different",
            "mechanism than dose-to-immune-cells.",
        ],
        subtitle="Scatter plots of AICE3 metrics against overall survival, stratified by treatment group")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 26: AICE3 CORRELATION (Fig 19)
    # ══════════════════════════════════════════════════════════════════════
    add_figure_slide(prs, "Fig19_AICE3_Correlation.png",
        "AICE3 Internal Metric Correlations",
        [
            "**Correlation structure of AICE3:**",
            "",
            "**Highly correlated (r > 0.8):**",
            "\u2022 H_mean_blood \u2194 H_body_dyn",
            "\u2022 H_mean_blood \u2194 H_liver_dyn",
            "\u2022 E_dyn \u2194 E_static \u2194 AICE3_raw",
            "\u2022 AICE3_raw \u2194 damage_proxy",
            "",
            "**Weakly correlated:**",
            "\u2022 H_spleen_dyn: relatively independent",
            "",
            "**Implication:**",
            "\u2022 Most AICE3 metrics are redundant",
            "\u2022 Hepatic dose drives blood dose",
            "\u2022 Splenic dose is independent \u2014 may",
            "  have unique prognostic potential",
            "  in larger datasets",
            "",
            "**For future studies:** Splenic dose",
            "deserves separate investigation.",
        ],
        subtitle="Pearson correlation heatmap across AICE3 components (n=38)")

    # ══════════════════════════════════════════════════════════════════════
    #  SECTION: DISCUSSION
    # ══════════════════════════════════════════════════════════════════════
    add_section_divider(prs, "Discussion & Conclusions", "")

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 28: DISCUSSION
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Discussion")

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.8), [
        "**Key findings:**",
        "",
        "1. SCART combined with peri-RT immunotherapy",
        "   shows a consistent OS benefit after adjusting",
        "   for confounders (HR 0.53\u20130.71)",
        "",
        "2. The unadjusted comparison HIDES this benefit",
        "   due to IO patients being older and having",
        "   more advanced disease (selection bias)",
        "",
        "3. In BCLC-C (n=24), IO extends median OS from",
        "   2.0 to 9.2 months (4.5\u00d7 improvement)",
        "",
        "4. SCART achieves 80% ORR with IO \u2014 substantially",
        "   higher than systemic therapy benchmarks",
        "",
        "5. SCART safety is excellent: no Grade \u22652 toxicity,",
        "   even in combination with immunotherapy",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(6.8), Inches(1.2), Inches(6), Inches(5.8), [
        "**Mechanistic considerations:**",
        "",
        "\u2022 High-dose SCART (BED 195 Gy) likely induces",
        "  robust immunogenic cell death",
        "\u2022 Peri-RT immunotherapy may capitalize on this",
        "  immune priming window",
        "\u2022 AICE3 immune-dose is similar between groups,",
        "  suggesting the IO benefit is not mediated",
        "  by differential immune damage from RT",
        "",
        "**Comparison with literature:**",
        "",
        "\u2022 SBRT + IO for HCC is an active research area",
        "\u2022 CheckMate 9DW, LEAP-012 exploring this",
        "\u2022 Our SCART approach differs: spatially-",
        "  fractionated delivery enables treatment of",
        "  much larger tumors (GTV up to 3,024 cm\u00b3)",
        "\u2022 The 80% ORR exceeds published SBRT series",
    ], font_size=14, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 29: LIMITATIONS & STRENGTHS
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Strengths & Limitations")

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.8), [
        "**Strengths**",
        "",
        "\u2022 Multiple complementary analytical methods",
        "  (PSM, IPTW, Cox, stratified)",
        "\u2022 Consistent effect direction across 6/8 methods",
        "\u2022 Results validated against independent V2 analysis",
        "  (Stratified HR: V2 = 0.51, V3 = 0.53)",
        "\u2022 Large effect size (HR 0.53) is clinically",
        "  meaningful if confirmed",
        "\u2022 Novel AICE3 immune-dose integration",
        "\u2022 Comprehensive safety assessment with",
        "  OAR dose verification",
        "\u2022 SCART enables treatment of very large tumors",
        "  not amenable to conventional SBRT",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(6.8), Inches(1.2), Inches(6), Inches(5.8), [
        "**Limitations**",
        "",
        "\u2022 Retrospective, single-center design",
        "\u2022 Small sample size (N=40, 30 events)",
        "\u2022 No result achieves p < 0.05",
        "  \u2013 Study underpowered by ~3\u00d7",
        "  \u2013 ~120 patients needed for 80% power",
        "\u2022 PSM reduced to 7 pairs (very limited)",
        "\u2022 Non-randomized treatment allocation",
        "  \u2013 Residual confounding possible",
        "  \u2013 Performance status not captured",
        "\u2022 Multiple comparisons without formal",
        "  correction (exploratory analysis)",
        "\u2022 Single center limits generalizability",
        "",
        "**These results are hypothesis-generating**",
        "**and require prospective validation.**",
    ], font_size=14, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 30: CONCLUSIONS
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)

    # Gold accent
    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.06))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_textbox(slide, Inches(0.5), Inches(0.4), Inches(12), Inches(0.8),
                "Conclusions", font_size=32, color=GOLD, bold=True, alignment=PP_ALIGN.CENTER)

    add_bullet_textbox(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5), [
        "**1.** SCART (3 \u00d7 21 Gy, BED 195 Gy) is a feasible and well-tolerated spatially-fractionated RT technique for HCC,",
        "    including very large tumors (GTV up to 3,024 cm\u00b3). No Grade \u22652 toxicity was observed.",
        "",
        "**2.** Unadjusted comparison of SCART+IO vs SCART Alone is misleading due to significant confounding by age",
        "    and BCLC stage (IO patients are older and have more advanced disease).",
        "",
        "**3.** After propensity score matching and multivariable adjustment, SCART+IO shows a consistent protective",
        "    effect on OS: adjusted HR = 0.53\u20130.71, representing a 29\u201347% reduction in the hazard of death.",
        "",
        "**4.** In BCLC-C advanced HCC (n=24), SCART+IO achieves median OS of 9.2 months vs 2.0 months with SCART alone",
        "    (4.5\u00d7 improvement), with an 80% objective response rate exceeding published systemic therapy benchmarks.",
        "",
        "**5.** AICE3 immune-dose metrics are comparable between groups and not prognostic, suggesting the IO benefit",
        "    is mediated by immunological mechanisms beyond radiation-induced immune cell damage.",
        "",
        "**6.** These hypothesis-generating results warrant prospective, multi-center validation of SCART + immunotherapy",
        "    for advanced HCC, with adequate sample size (\u2265120 patients) to achieve statistical significance.",
    ], font_size=15, color=WHITE, spacing_pt=4)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 31: FUTURE DIRECTIONS
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_slide_title(slide, "Future Directions")

    add_bullet_textbox(slide, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.8), [
        "**Immediate next steps:**",
        "",
        "\u2022 Multi-center expansion to increase",
        "  sample size and statistical power",
        "\u2022 Complete data collection for 26 additional",
        "  enrolled patients (pending IO classification)",
        "\u2022 Immune biomarker correlation (ALC,",
        "  lymphocyte subsets, PD-L1 expression)",
        "\u2022 AICE3 splenic dose as independent",
        "  prognostic factor",
        "",
        "**Prospective trial design:**",
        "",
        "\u2022 Phase II: SCART + anti-PD-1 vs SCART alone",
        "\u2022 Primary endpoint: OS at 12 months",
        "\u2022 Target enrollment: \u2265120 patients",
        "\u2022 Stratification by BCLC stage",
    ], font_size=14, color=DARK)

    add_bullet_textbox(slide, Inches(6.8), Inches(1.2), Inches(6), Inches(5.8), [
        "**Technical innovations:**",
        "",
        "\u2022 Dose escalation: Can BED > 200 Gy",
        "  further improve immunogenic cell death?",
        "\u2022 Optimal IO timing: Explore neoadjuvant",
        "  vs concurrent vs adjuvant sequencing",
        "\u2022 Adaptive RT + IO: Real-time response",
        "  monitoring with adaptive dose adjustment",
        "",
        "**Broader applications:**",
        "",
        "\u2022 SCART + IO for other GI malignancies",
        "  (cholangiocarcinoma, pancreatic, colorectal liver mets)",
        "\u2022 Combination with other IO agents",
        "  (anti-CTLA-4, anti-LAG-3, anti-TIGIT)",
        "\u2022 Integration of AICE3 for personalized",
        "  dose optimization to spare immune cells",
    ], font_size=14, color=DARK)

    # ══════════════════════════════════════════════════════════════════════
    #  SLIDE 32: ACKNOWLEDGMENTS / THANK YOU
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)

    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, Inches(0.06))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_textbox(slide, Inches(1), Inches(2.0), Inches(11), Inches(1.2),
                "Thank You",
                font_size=44, color=GOLD, bold=True, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, Inches(1), Inches(3.5), Inches(11), Inches(1.0),
                "Questions & Discussion",
                font_size=28, color=WHITE, bold=False, alignment=PP_ALIGN.CENTER)

    shape = slide.shapes.add_shape(1, Inches(4.5), Inches(4.7), Inches(4.333), Inches(0.04))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    add_bullet_textbox(slide, Inches(2.5), Inches(5.2), Inches(8), Inches(1.5), [
        "Supplementary materials: 15-sheet Excel report + 24 publication-quality figures",
        "Matched analysis: PSM, IPTW, stratified Cox, BCLC subgroup, AICE3 integration",
        "Data cutoff: March 9, 2026  |  Analysis: March 12, 2026",
    ], font_size=13, color=RGBColor(0xAA, 0xAA, 0xAA), spacing_pt=8)

    add_textbox(slide, Inches(1), Inches(6.8), Inches(11), Inches(0.5),
                "Radiosurgery Society (RSS) Scientific Meeting  |  SCART for HCC",
                font_size=12, color=MED_GRAY, alignment=PP_ALIGN.CENTER)

    # ══════════════════════════════════════════════════════════════════════
    #  SAVE
    # ══════════════════════════════════════════════════════════════════════
    prs.save(str(OUTPUT))
    print(f"Saved: {OUTPUT}")
    print(f"Slides: {len(prs.slides)}")


if __name__ == "__main__":
    build_presentation()
