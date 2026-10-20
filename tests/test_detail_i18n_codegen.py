import json
from pathlib import Path

from onesite.codegen.i18n import generate_locale_files


TEMPLATE_DIR = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def test_empty_result_translation_key_matches_detail_template(tmp_path):
    generate_locale_files([], tmp_path)

    en = json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))
    detail_template = (TEMPLATE_DIR / "frontend_page_detail.tsx.j2").read_text(encoding="utf-8")
    list_template = (TEMPLATE_DIR / "frontend_page_list.tsx.j2").read_text(encoding="utf-8")

    assert en["common"]["no_result"] == "No result"
    assert zh["common"]["no_result"] == "暂无数据"
    assert en["common"]["compact"] == "Compact"
    assert zh["common"]["compact"] == "紧凑"
    assert en["common"]["no_matching_point"] == "No matching point"
    assert zh["common"]["no_matching_point"] == "没有匹配的点位"
    assert "t('common.no_result')" in detail_template
    assert "t('common.no_result')" in list_template
    assert "common.no result" not in list_template


def test_detail_relation_titles_use_translated_plural():
    template = (TEMPLATE_DIR / "frontend_page_detail.tsx.j2").read_text(encoding="utf-8")

    assert "models.{{ m2m.target_service }}.plural" in template
    assert "models.{{ rel.source_service }}.plural" in template
    assert "models.{{ rfk.source_service }}.plural" in template
    assert ".name')}s</CardTitle>" not in template
