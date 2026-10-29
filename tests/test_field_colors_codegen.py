"""Field color validation, generated views, and runtime behavior."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlmodel import Field, SQLModel

from onesite.codegen.metadata.colors import PRESET_COLORS, normalize_color
from onesite.codegen.phases.introspect_models import _introspect_module
from test_read_fields_codegen import _template

CONFIG = {
    "rules": [
        {"when": {"eq": "ACTIVE"}, "color": "red"},
        {"when": {"eq": "RECOVERED"}, "color": "green"},
    ],
    "default": "gray",
}


class ColoredRecord(SQLModel, table=True):
    __tablename__ = "test_colored_record"
    __onesite__ = {"row_color": {
        "rules": [{"when": {"field": "status", "eq": "ACTIVE"}, "color": "red"}],
        "default": "green",
    }}
    id: int | None = Field(default=None, primary_key=True)
    status: str = Field(sa_column_kwargs={"info": {"site_props": {"color": CONFIG}}})
    title: str = Field(
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "component": "badge",
                    "color": {
                        "rules": [{"when": {"field": "status", "eq": "ACTIVE"}, "color": "rose"}]
                    },
                }
            }
        }
    )


def normalize(value):
    return normalize_color(
        value, field_name="status", field_names={"status", "title"}, location="ColoredRecord.status"
    )


def test_validation_and_presets():
    assert len(PRESET_COLORS) == 17
    assert normalize("blue") == "blue"
    assert normalize(None) is None
    assert normalize(CONFIG)["rules"][0]["when"] == {"field": "status", "eq": "ACTIVE"}


@pytest.mark.parametrize(
    "value",
    [
        "unknown",
        {},
        {"rules": []},
        {"rules": [None]},
        {"rules": [{"when": {"field": "missing", "eq": 1}, "color": "red"}]},
        {"rules": [{"when": {"eq": 1, "ne": 2}, "color": "red"}]},
        {"rules": [{"when": {"contains": "x"}, "color": "red"}]},
        {"rules": [{"when": {"gt": True}, "color": "red"}]},
        {"rules": [{"when": {"in": "ACTIVE"}, "color": "red"}]},
        {"rules": [{"when": {"eq": {}}, "color": "red"}]},
        {"rules": CONFIG["rules"], "default": "bad"},
    ],
)
def test_rejects_invalid_configuration(value):
    with pytest.raises(ValueError, match=r"ColoredRecord.status.color"):
        normalize(value)


def test_all_views_render_color_configuration():
    model = _introspect_module(
        type("Module", (), {"ColoredRecord": ColoredRecord}), "colored_record"
    )[0]
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_definition_bindings=[],
        definition_binding_meta=None,
        is_timescaledb=False,
        is_notification_table=False,
        min_role_for_read="USER",
        min_role_for_create="USER",
        min_role_for_update="USER",
        min_role_for_delete="USER",
        has_dynamic_action_states=False,
    )
    assert model.fields[1].color == normalize(CONFIG)
    for mode in ("list", "grid"):
        model["list_mode"] = mode
        page = _template("frontend_page_list.tsx.j2", model)
        assert "<FieldColor config={" in page
        if mode == "list":
            assert '<TableRow key={item.id} className={resolveRowColorClass(' in page
            assert json.dumps(model.site_props["row_color"], sort_keys=True) in page
        assert "record={ item as unknown as Record<string, unknown>}" in page
        assert "canRead={(name) => hasFieldPerm(name, 'r')}" in page
    page = _template("frontend_page_detail.tsx.j2", model)
    assert "record={ currentItem as unknown as Record<string, unknown>}" in page
    assert 'field="title"' in page


def test_runtime_matching(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the frontend resolver")
    source = Path("src/onesite/templates/frontend/src/components/ui/field-color.tsx").read_text()
    # Node's type stripping executes the actual resolver without a JSX build.
    resolver = source[
        source.index("export function resolveFieldColor") : source.index(
            "export function FieldColor("
        )
    ]
    script = tmp_path / "colors.mts"
    script.write_text(
        'import assert from "node:assert/strict";\n'
        + source[source.index("export const ROW_COLORS"):source.index("type Color =")]
        + resolver
        + source[source.index("export function resolveRowColorClass"):]
        + "\n"
        + """
const config = """
        + json.dumps(normalize(CONFIG))
        + """;
const read = () => true;
assert.equal(resolveFieldColor(config, 'status', {status: 'ACTIVE'}, read), 'red');
assert.equal(resolveFieldColor(config, 'status', {status: 'RECOVERED'}, read), 'green');
assert.equal(resolveFieldColor(config, 'status', {status: 'OTHER'}, read), 'gray');
assert.equal(resolveFieldColor(config, 'status', {}, read), 'gray');
assert.equal(resolveFieldColor(config, 'status', {status: 'ACTIVE'}, () => false), 'gray');
assert.equal(resolveFieldColor('blue', 'status', {}, read), 'blue');
const rowConfig = {rules: [{when: {field: 'status', eq: 'ACTIVE'}, color: 'red'}]};
assert.equal(resolveRowColorClass(rowConfig, {status: 'ACTIVE'}, read), ROW_COLORS.red);
assert.equal(resolveRowColorClass(rowConfig, {status: 'OTHER'}, read), '');
assert.equal(resolveRowColorClass(rowConfig, {}, read), '');
assert.equal(resolveRowColorClass(rowConfig, {status: 'ACTIVE'}, () => false), '');
assert.equal(resolveRowColorClass({...rowConfig, default: 'green'}, {}, read), ROW_COLORS.green);
assert.equal(resolveRowColorClass('blue', {}, read), ROW_COLORS.blue);
for (const [op, value] of [['eq', 5], ['ne', 6], ['in', [5, 6]], ['gt', 4], ['gte', 5], ['lt', 6], ['lte', 5]]) {
 const rule = {rules: [{when: {field: 'count', [op]: value}, color: 'red'}, {when: {eq: 5}, color: 'green'}]};
 assert.equal(resolveFieldColor(rule, 'status', {count: 5, status: 5}, read), 'red');
}
assert.equal(resolveFieldColor({rules: [{when: {gt: 1}, color: 'red'}]}, 'status', {status: '5'}, read), undefined);
assert.equal(resolveFieldColor({rules: [{when: {eq: null}, color: 'red'}]}, 'status', {status: null}, read), 'red');
"""
    )
    subprocess.run(
        [node, "--experimental-strip-types", str(script)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_sync_copies_color_component(tmp_path):
    from onesite.codegen.assets import sync_frontend_assets
    from onesite.project_paths import get_project_paths
    from test_rtsp_preview_codegen import _config

    sync_frontend_assets(tmp_path, _config())
    component = get_project_paths(tmp_path).frontend / "src/components/ui/field-color.tsx"
    assert component.exists()
    for color in PRESET_COLORS:
        assert f"text-{color}-700" in component.read_text()


def test_model_row_color_requires_explicit_existing_field():
    from onesite.codegen.introspect import get_model_fields

    original = ColoredRecord.__onesite__
    try:
        for when in ({"eq": "ACTIVE"}, {"field": "missing", "eq": "ACTIVE"}):
            ColoredRecord.__onesite__ = {"row_color": {
                "rules": [{"when": when, "color": "red"}],
            }}
            with pytest.raises(ValueError, match=r"ColoredRecord.row_color"):
                get_model_fields(ColoredRecord)
    finally:
        ColoredRecord.__onesite__ = original


def test_unconfigured_model_has_no_row_coloring():
    original = ColoredRecord.__onesite__
    try:
        ColoredRecord.__onesite__ = {}
        model = _introspect_module(
            type("Module", (), {"ColoredRecord": ColoredRecord}), "colored_record"
        )[0]
        page = _template("frontend_page_list.tsx.j2", model)
        assert "resolveRowColorClass" not in page
        assert '<TableRow key={item.id}>' in page
    finally:
        ColoredRecord.__onesite__ = original
