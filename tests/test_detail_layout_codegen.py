"""Coverage for model-configured detail page layouts."""

from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class LayoutRecord(SQLModel, table=True):
    __tablename__ = "test_detail_layout_record"
    __onesite__ = {
        "page_edit": True,
        "ui": {
            "detail": {
                "layout": [
                    {
                        "section": "basic",
                        "title": "Basic information",
                        "items": [["title", "endpoint"]],
                    },
                    [
                        {
                            "section": "connection",
                            "title": "Connection settings",
                            "span": 1,
                            "items": ["is_enabled"],
                        },
                        {
                            "section": "advanced",
                            "title": "Advanced settings",
                            "span": 2,
                            "items": ["timeout"],
                        },
                    ],
                ]
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    endpoint: str
    is_enabled: bool = True
    timeout: int = 30
    notes: str = ""


class LayoutForeignTarget(SQLModel, table=True):
    __tablename__ = "test_layout_foreign_target"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class LayoutForeignRecord(SQLModel, table=True):
    __tablename__ = "test_layout_foreign_record"
    __onesite__ = {
        "page_edit": True,
        "ui": {"detail": {"layout": [["title", "target_id"]]}},
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    target_id: Optional[int] = Field(
        default=None, foreign_key="test_layout_foreign_target.id"
    )


class ConfiguredFormForeignRecord(SQLModel, table=True):
    __tablename__ = "test_configured_form_foreign_record"
    __onesite__ = {
        "page_edit": True,
        "ui": {
            "detail": {"layout": [["target_id"]]},
            "form": {"layout": [["target_id", "title"]]},
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    target_id: Optional[int] = Field(
        default=None,
        foreign_key="test_layout_foreign_target.id",
        sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}},
    )


def _model():
    result = get_model_fields(LayoutRecord, "layout_record")
    return _build_model_dict("LayoutRecord", "layout_record", "layout_record", result)


def test_detail_layout_normalizes_section_rows_and_preserves_field_order():
    model = _model()

    assert model.detail_layout[0]["kind"] == "row"
    assert model.detail_layout[0]["items"][0]["section"] == "basic"
    assert model.detail_layout[0]["items"][0]["items"][0]["columns"] == 2
    assert model.detail_layout[1]["columns"] == 3
    assert [item["span"] for item in model.detail_layout[1]["items"]] == [1, 2]
    # Fields absent from the explicit layout are retained in model declaration
    # order, so adding UI configuration never accidentally hides `notes`.
    assert model.detail_layout[-1]["items"][0]["field"] == "notes"


def test_detail_layout_is_emitted_into_the_generated_page():
    model = _model()
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert 'const hasDetailLayout = detailLayout.length > 0;' in rendered
    assert '"title": "Basic information"' in rendered
    assert "renderDetailLayoutNode" in rendered
    assert "activeTab === 'detail' && hasDetailLayout" in rendered
    assert "const renderDetailEditField" in rendered
    assert "renderDetailLayoutNode(node, `detail-layout-${index}`, true)" in rendered
    assert "detail_read_field" not in rendered


def test_page_edit_create_page_uses_the_normalized_form_layout():
    model = _model()
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_create.tsx.j2"
    ).render(model=model)

    assert "const createLayout = " in rendered
    assert '"title": "Basic information"' in rendered
    assert "renderFormLayoutNode" in rendered
    assert "createLayout.map((node, index)" in rendered
    assert "case 'title':" in rendered
    assert "case 'endpoint':" in rendered
    assert "md:grid-cols-3" in rendered
    # The create form uses the same section cards as the detail editor without
    # adding another model-level card around the whole page.
    assert 'id="create-form"' in rendered
    assert 'form="create-form"' in rendered
    assert '<CardTitle>{t(\'models.layout_record.name\')}</CardTitle>' not in rendered
    assert 'data-page-region="form-actions"' not in rendered


def test_page_edit_layout_includes_editable_foreign_keys():
    result = get_model_fields(LayoutForeignRecord, "layout_foreign_record")
    model = _build_model_dict(
        "LayoutForeignRecord", "layout_foreign_record", "layout_foreign_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert model.detail_layout[0]["items"][1]["field"] == "target_id"
    assert 'const editLayout = ' in rendered
    assert "case 'target_id':" in rendered
    assert 'name="target_id"' in rendered
    assert "getTestLayoutForeignTargets(1, 20, filters)" in rendered
    assert "detailLayout.map((node, index)" in rendered


def test_page_edit_accepts_an_explicit_foreign_key_form_layout():
    result = get_model_fields(ConfiguredFormForeignRecord, "configured_form_foreign_record")
    model = _build_model_dict(
        "ConfiguredFormForeignRecord",
        "configured_form_foreign_record",
        "configured_form_foreign_record",
        result,
    )

    first_row = model.form_layout[0]
    assert [item["field"] for item in first_row["items"]] == ["target_id", "title"]

    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)
    target_case = rendered.split("case 'target_id':", 1)[1].split("default:", 1)[0]
    assert "currentItem.target_id_label ?? currentItem.target_id" in target_case
    assert 'name="target_id"' not in target_case

    create_rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_create.tsx.j2"
    ).render(model=model)
    create_layout_source = create_rendered.split("const createLayout = ", 1)[1].split(
        " as any[];", 1
    )[0]
    assert '"field": "target_id"' not in create_layout_source
    assert '{"field": "title", "kind": "field", "span": 1}' in create_layout_source


def test_detail_layout_rejects_unknown_or_duplicate_fields():
    original = LayoutRecord.__onesite__["ui"]["detail"]["layout"]
    try:
        LayoutRecord.__onesite__["ui"]["detail"]["layout"] = ["missing"]
        with pytest.raises(ValueError, match="field 'missing'"):
            _model()

        LayoutRecord.__onesite__["ui"]["detail"]["layout"] = ["title", "title"]
        with pytest.raises(ValueError, match="configured more than once"):
            _model()
    finally:
        LayoutRecord.__onesite__["ui"]["detail"]["layout"] = original


def test_form_only_layout_drives_detail_and_both_editing_containers():
    original = LayoutRecord.__onesite__
    try:
        LayoutRecord.__onesite__ = {
            "page_edit": True,
            "ui": {"form": {"layout": [{
                "section": "settings", "title": "Settings",
                "items": [["title", "endpoint"], "is_enabled"],
            }]}},
        }
        model = _model()
        assert model.detail_layout[0]["items"][0]["section"] == "settings"
        assert model.create_layout[0] == model.edit_layout[0]
        env = Environment(loader=FileSystemLoader(
            Path(__file__).parents[1] / "src/onesite/templates/codegen"
        ))
        page = env.get_template("frontend_page_detail.tsx.j2").render(model=model)
        assert "editLayout.map((node, index)" in page
        assert "disabled={isEditing}" not in page  # no related tabs on this model
        model.page_edit = False
        model.edit_mode = "modal"
        modal = env.get_template("frontend_page_list.tsx.j2").render(model=model)
        assert 'const formLayout = (editingId' in modal
        assert '"title": "Settings"' in modal
    finally:
        LayoutRecord.__onesite__ = original


def test_edit_layout_excludes_create_only_fields_without_grid_gaps():
    from onesite.codegen.phases.introspect_models import _form_layout_from_detail_layout

    layout = [{"kind": "row", "columns": 2, "items": [
        {"kind": "field", "field": "password", "span": 1},
        {"kind": "field", "field": "title", "span": 1},
    ]}]
    assert _form_layout_from_detail_layout(layout, ["title"]) == [{
        "kind": "row", "columns": 1,
        "items": [{"kind": "field", "field": "title", "span": 1}],
    }]
