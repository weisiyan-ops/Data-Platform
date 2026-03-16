from app.utils.accuray_helpers import (
    extract_chart_sections,
    extract_name_from_chart_stem,
    normalize_patient_name,
)


def test_normalize_patient_name_handles_aliases_and_copy_suffix() -> None:
    assert normalize_patient_name("陈海福 - Copy") == "陈海福"
    assert normalize_patient_name("叶立葵") == "叶立奎"


def test_extract_name_from_chart_stem_strips_date_suffix() -> None:
    assert extract_name_from_chart_stem("孙杏清 2020-11") == "孙杏清"
    assert extract_name_from_chart_stem("何钊友 2025-02-04") == "何钊友"


def test_extract_chart_sections_groups_lines_by_header() -> None:
    lines = [
        "主诉：反复右上腹痛4月余。",
        "现病史：患者于2020-07-01发现肝占位。",
        "曾于外院行介入治疗。",
        "既往史：高血压病史10年。",
        "个人史：否认吸烟饮酒。",
        "家族史：否认家族遗传病史。",
        "初步诊断：原发性肝癌。",
    ]

    sections = extract_chart_sections(lines)

    assert sections["chief_complaint"] == "反复右上腹痛4月余。"
    assert sections["present_illness"] == "患者于2020-07-01发现肝占位。\n曾于外院行介入治疗。"
    assert sections["past_history"] == "高血压病史10年。"
    assert sections["personal_history"] == "否认吸烟饮酒。"
    assert sections["family_history"] == "否认家族遗传病史。"
    assert sections["preliminary_diagnosis"] == "原发性肝癌。"
