"""Regression coverage for type-safe JSON-backed submodels."""

from datetime import date, datetime, time
from pathlib import Path
import sys
import types

from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError
import pytest
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class TypedJsonConfig(SQLModel):
    retries: int = Field(..., ge=1, le=10, description="Retry count")
    ratio: float | None = Field(default=None, ge=0, le=1)
    enabled: bool
    run_date: date
    run_at: datetime
    cutoff: time
    labels: dict[str, str] = Field(default_factory=dict)
    ports: list[int] = Field(default_factory=list)


class TypedJsonRecord(SQLModel, table=True):
    __tablename__ = "test_typed_json_record"

    id: int | None = Field(default=None, primary_key=True)
    priority: int = Field(ge=1, le=5)
    # Explicit UI configuration must not erase the annotated submodel.
    config: TypedJsonConfig | None = Field(
        sa_column=Column(JSON, info={"site_props": {"component": "json"}}),
    )
    configs: list[TypedJsonConfig | None] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    configs_by_name: dict[str, TypedJsonConfig] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    raw_options: dict | None = Field(default=None, sa_column=Column(JSON))


def _render_schema():
    result = get_model_fields(TypedJsonRecord, "typed_json_record")
    model = _build_model_dict(
        "TypedJsonRecord", "typed_json_record", "typed_json_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "schema.py.j2"
    ).render(model=model)
    return result, rendered


def test_pep604_submodels_keep_their_json_schema_and_input_types():
    result, _ = _render_schema()
    fields = {field.name: field for field in result.fields}

    assert fields["config"].type == "Optional[TypedJsonConfig]"
    assert fields["config"].ui_type == "json"
    assert fields["config"].json_model_schema is not None
    assert fields["configs"].type == "List[Optional[TypedJsonConfig]]"
    assert fields["configs"].json_item_schema is not None
    assert fields["configs_by_name"].json_item_schema is not None
    assert fields["raw_options"].type == "Optional[Dict[str, Any]]"
    assert fields["priority"].minimum == 1
    assert fields["priority"].maximum == 5

    schema_fields = {
        field["name"]: field for field in fields["config"].json_model_schema["fields"]
    }
    assert schema_fields["retries"]["kind"] == "int"
    assert schema_fields["retries"]["required"] is True
    assert schema_fields["retries"]["minimum"] == 1
    assert schema_fields["retries"]["maximum"] == 10
    assert schema_fields["ratio"]["kind"] == "float"
    assert schema_fields["ratio"]["nullable"] is True
    assert schema_fields["ratio"]["minimum"] == 0
    assert schema_fields["ratio"]["maximum"] == 1
    assert schema_fields["enabled"]["kind"] == "bool"
    assert schema_fields["run_date"]["kind"] == "date"
    assert schema_fields["run_at"]["kind"] == "datetime"
    assert schema_fields["cutoff"]["kind"] == "time"
    assert schema_fields["labels"]["kind"] == "object"
    assert schema_fields["ports"]["item"]["kind"] == "int"


def test_generated_api_schema_validates_submodel_field_types(monkeypatch):
    _, rendered = _render_schema()

    app_module = types.ModuleType("app")
    models_module = types.ModuleType("app.models")
    source_module = types.ModuleType("app.models.typed_json_record")
    source_module.TypedJsonRecord = TypedJsonRecord
    source_module.TypedJsonConfig = TypedJsonConfig
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.models", models_module)
    monkeypatch.setitem(sys.modules, "app.models.typed_json_record", source_module)

    # Load the real shared schema authorization base into this isolated package.
    import importlib.util
    access_path = Path(__file__).parents[1] / "src/onesite/templates/backend/app/core/access.py"
    access_spec = importlib.util.spec_from_file_location("app.core.access", access_path)
    access = importlib.util.module_from_spec(access_spec)
    access_spec.loader.exec_module(access)
    monkeypatch.setitem(sys.modules, "app.core", types.ModuleType("app.core"))
    monkeypatch.setitem(sys.modules, "app.core.access", access)

    namespace: dict[str, object] = {}
    exec(compile(rendered, "generated_schema.py", "exec"), namespace)
    create_schema = namespace["TypedJsonRecordCreate"]

    valid = create_schema(
        priority=3,
        config={
            "retries": 3,
            "enabled": True,
            "run_date": "2026-09-01",
            "run_at": "2026-09-01T08:30:00",
            "cutoff": "17:00:00",
            "labels": {"environment": "production"},
            "ports": [8000, 8001],
        }
    )
    assert isinstance(valid.config, TypedJsonConfig)
    assert valid.config.retries == 3

    with pytest.raises(ValidationError):
        create_schema(
            priority=3,
            config={
                "retries": "not-an-integer",
                "enabled": "not-a-boolean",
                "run_date": "not-a-date",
                "run_at": "not-a-datetime",
                "cutoff": "not-a-time",
                "ports": ["not-an-integer"],
            }
        )


def test_registration_and_profile_forms_use_the_typed_submodel_editor():
    result = get_model_fields(TypedJsonRecord, "typed_json_record")
    model = _build_model_dict(
        "TypedJsonRecord", "typed_json_record", "typed_json_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    register_page = environment.get_template("register_page.tsx.j2").render(model=model)
    profile_page = environment.get_template("profile.tsx.j2").render(model=model)

    assert "const rootValue = watch();" in register_page
    assert "<JsonModelEditor" in register_page
    assert '"kind": "int"' in register_page
    assert "<JsonModelEditor" in profile_page
    assert "<JsonModelDetail" in profile_page


def test_generated_frontend_enforces_model_and_submodel_numeric_constraints():
    result = get_model_fields(TypedJsonRecord, "typed_json_record")
    model = _build_model_dict(
        "TypedJsonRecord", "typed_json_record", "typed_json_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)
    list_page = environment.get_template("frontend_page_list.tsx.j2").render(model=model)
    singleton_page = environment.get_template("singleton_page.tsx.j2").render(model=model)
    settings_page = environment.get_template("settings_page.tsx.j2").render(
        system_model=model, custom_model=None
    )
    editor = (
        Path(__file__).parents[1]
        / "src/onesite/templates/frontend/src/components/ui/json-model-editor.tsx"
    ).read_text()

    for rendered in (create_page, list_page):
        assert "min={ 1 }" in rendered
        assert "max={ 5 }" in rendered
        assert "validateJsonModelValue" in rendered
        assert '"minimum": 1' in rendered
        assert '"maximum": 10' in rendered
        assert 'className="text-destructive"> *</span>' in rendered

    assert "export const validateJsonModelValue" in editor
    assert "fieldValue < field.minimum" in editor
    assert "fieldValue > field.maximum" in editor
    assert "min={f.minimum}" in editor
    assert "max={f.maximum}" in editor
    assert "{field.required && <span className=\"text-destructive\"> *</span>}" in editor
    assert 'if (!isArray && (!key.trim() || key.startsWith("__new_"))) return "Key is required"' in editor
    assert '{t("json_editor.key")}<span className="text-destructive"> *</span>' in editor
    assert "<JsonModelDictEditor" in singleton_page
    assert "validateJsonModelCollectionValue" in singleton_page
    assert "<JsonModelDictEditor" in settings_page
