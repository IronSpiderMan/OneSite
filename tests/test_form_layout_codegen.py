"""Coverage for model and JSON-submodel form layouts."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class AuthConfig(BaseModel):
    __onesite__ = {
        "ui": {
            "detail": {
                "layout": [
                    ["client_id", "client_secret"],
                    {"section": "options", "title": "Options", "items": ["enabled"]},
                ]
            }
        }
    }

    client_id: str = ""
    client_secret: str = ""
    enabled: bool = True


class FormLayoutRecord(SQLModel, table=True):
    __tablename__ = "test_form_layout_record"
    __onesite__ = {
        "ui": {
            "detail": {
                "layout": [
                    ["title", "endpoint"],
                    {"section": "connection", "title": "Connection", "items": ["is_enabled"]},
                ]
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    endpoint: str
    is_enabled: bool = True
    auth_config: AuthConfig = Field(default_factory=AuthConfig, sa_column=Column(JSON))


def _model():
    result = get_model_fields(FormLayoutRecord, "form_layout_record")
    return _build_model_dict("FormLayoutRecord", "form_layout_record", "form_layout_record", result)


def test_modal_form_uses_its_own_ui_form_layout():
    model = _model()

    assert model.form_layout[0]["columns"] == 2
    assert model.form_layout[1]["items"][0]["title"] == "Connection"
    # Fields omitted from the configured layout remain editable.
    assert model.form_layout[-1]["items"][0]["field"] == "auth_config"

    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)

    assert 'const formLayout = ' in rendered
    assert '"title": "Connection"' in rendered
    assert "renderModalFormLayoutNode" in rendered
    assert "'title': (!(embedded && relationField === 'title'" in rendered
    assert "&& (!editingId ? hasFieldPerm('title', 'c')" in rendered
    assert "const payload = writablePayload({ ...values, ...fixedFields }" in rendered
    assert "'title': ({(!editingId" not in rendered
    assert "const [isSaving, setIsSaving] = useState(false);" in rendered
    assert '<Button type="submit" disabled={isSaving}>' in rendered
    assert "t('common.saving', 'Saving...')" in rendered
    assert "t('common.deleting', 'Deleting...')" in rendered
    assert rendered.count('animate-spin') >= 3
    assert rendered.count("event.preventDefault();") >= 2
    assert "void confirmBulkDelete();" in rendered
    assert "if (!isBulkDeleting) setBulkDeleteOpen(open);" in rendered

    service = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_service.ts.j2"
    ).render(model=model)
    assert "`${API_URL}/bulk_delete`, { ids }, { suppressErrorToast: true }" in service


def test_json_submodel_emits_and_uses_its_own_form_layout():
    result = get_model_fields(FormLayoutRecord, "form_layout_record")
    auth_field = next(field for field in result.fields if field.name == "auth_config")

    assert auth_field.json_model_schema["layout"][0]["items"][0]["field"] == "client_id"
    assert auth_field.json_model_schema["layout"][1]["items"][0]["title"] == "Options"

    component = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "json-model-editor.tsx"
    ).read_text(encoding="utf-8")
    assert "schema.layout?.length" in component
    assert "renderLayoutNode" in component

    model = _model()
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)
    assert "import { JsonModelDetail }" in detail_page
    assert "<JsonModelDetail schema=" in detail_page


def test_default_forms_do_not_inherit_the_automatic_detail_section():
    class DefaultFormRecord(SQLModel, table=True):
        __tablename__ = "test_default_form_record"
        id: Optional[int] = Field(default=None, primary_key=True)
        title: str

    result = get_model_fields(DefaultFormRecord, "default_form_record")
    model = _build_model_dict("DefaultFormRecord", "default_form_record", "default_form_record", result)

    assert model.detail_layout[0]["items"][0]["title"] == "common.basic_information"
    for layout in (model.form_layout, model.create_layout, model.edit_layout):
        assert layout == [{"kind": "row", "columns": 1, "items": [
            {"kind": "field", "field": "title", "span": 1},
        ]}]


def test_list_modal_respects_field_visibility_conditions():
    model = _model()
    field = next(field for field in model.fields if field.name == "endpoint")
    field.visible_when = {"is_enabled": [True]}
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)
    endpoint_expression = next(
        line for line in rendered.splitlines() if "'endpoint': (!(embedded" in line
    )
    assert "&& ([true] as any[]).includes(rootValue?.['is_enabled'])" in endpoint_expression
