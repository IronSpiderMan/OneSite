"""Contract tests for the generated JSON editing experience."""

import json
from pathlib import Path

from onesite.codegen.i18n import generate_locale_files


def test_json_input_has_stable_draft_and_editor_affordances():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "json-input.tsx"
    ).read_text()

    assert "draftSignature(text) === valueSignature(value)" in source
    assert 'event.key !== "Tab"' in source
    assert 'event.key === "Enter"' in source
    assert "errorLocation(next, parseError)" in source
    assert 't("json_editor.format")' in source
    assert 't("json_editor.copy")' in source
    assert 'spellCheck={false}' in source


def test_json_input_height_tracks_content_with_a_maximum():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "json-input.tsx"
    ).read_text()

    assert "const MIN_EDITOR_HEIGHT = 120" in source
    assert "const MAX_EDITOR_HEIGHT = 384" in source
    assert "Math.max(textarea.scrollHeight, MIN_EDITOR_HEIGHT)" in source
    assert 'textarea.style.overflowY = textarea.scrollHeight > MAX_EDITOR_HEIGHT ? "auto" : "hidden"' in source
    assert "resize-none overflow-y-auto" in source


def test_json_editor_translations_are_generated():
    source = (
        Path(__file__).parents[1] / "src" / "onesite" / "codegen" / "i18n.py"
    ).read_text()

    assert source.count('"json_editor": {') == 2
    assert '"item_added": "New item added"' in source
    assert '"item_added": "已添加新项目"' in source
    assert '"syntax_error_at": "Invalid JSON near line {{line}}, column {{column}}"' in source
    assert '"syntax_error_at": "JSON 在第 {{line}} 行、第 {{column}} 列附近有误"' in source


def test_json_submodel_field_translations_are_emitted(tmp_path):
    schema = {
        "name": "AuthConfig",
        "fields": [
            {
                "name": "client_cert",
                "kind": "str",
                "labelKey": "json_models.auth_config.fields.client_cert",
                "translations": {"zh": "客户端证书"},
            }
        ],
    }
    models = [
        {
            "module_name": "connector",
            "name": "Connector",
            "fields": [
                {
                    "name": "auth_config",
                    "label_key": "models.connector.fields.auth_config",
                    "json_model_schema": schema,
                }
            ],
        }
    ]

    generate_locale_files(models, tmp_path)

    en = json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))
    assert en["json_models"]["auth_config"]["fields"]["client_cert"] == "Client Cert"
    assert zh["json_models"]["auth_config"]["fields"]["client_cert"] == "客户端证书"


def test_structured_json_editors_use_localized_familiar_controls():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "json-model-editor.tsx"
    ).read_text()

    assert "const EditorModeSwitch" in source
    assert 't("json_editor.form_mode")' in source
    assert 't("json_editor.source_mode")' in source
    assert 't("json_editor.add_item")' in source
    assert 'toast.success(t("json_editor.item_added"))' in source
    assert 't("common.remove")' in source
    assert "const [collapsedIndexes, setCollapsedIndexes]" in source
    assert 'aria-expanded={!collapsedIndexes.has(idx)}' in source
    assert "<ChevronDown" in source
    assert "<ChevronRight" in source
    assert "const [collapsedArrayItems, setCollapsedArrayItems]" in source


def test_detail_collection_editor_uses_inline_tables():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "json-model-editor.tsx"
    ).read_text()

    assert "export const JsonModelTableEditor" in source
    assert "foreignKeyLoaders?: JsonForeignKeyLoaders" in source
    assert "foreignKeyLoader={field.name ? foreignKeyLoaders?.[field.name] : undefined}" in source
    assert "export const JsonDynamicTableEditor" in source
    assert '<TableHead className="min-w-[10rem]">{t("json_editor.key")}<span className="text-destructive"> *</span></TableHead>' in source
    assert "<JsonTableCellEditor" in source
    assert '<TableHead className="w-[5rem]" />' in source
