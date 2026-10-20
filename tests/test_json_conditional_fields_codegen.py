"""Regression coverage for conditional fields inside typed JSON values."""

from enum import Enum
from pathlib import Path
import sys
import types
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class ValueType(str, Enum):
    float = "float"
    int = "int"
    string = "string"
    bool = "bool"
    enum = "enum"


def _conditional_props(visible_when: dict[str, list[str]], *, required: bool = False) -> dict:
    props = {
        "visible_when": visible_when,
        "clear_when_hidden": True,
    }
    if required:
        props["required_when"] = visible_when
    return {"info": {"site_props": props}}


class ConditionalJsonProperty(SQLModel):
    data_type: ValueType = Field(default=ValueType.float)
    enum_values: Optional[list[str]] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"data_type": ["enum"]}, required=True),
    )
    min_value: Optional[float] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"data_type": ["float", "int"]}),
    )
    max_value: Optional[float] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"data_type": ["float", "int"]}),
    )


class ConditionalJsonRecord(SQLModel, table=True):
    __tablename__ = "test_conditional_json_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    value: ConditionalJsonProperty = Field(sa_column=Column(JSON))
    values: list[ConditionalJsonProperty] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    values_by_key: dict[str, ConditionalJsonProperty] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )


class RootControlledProperties(SQLModel):
    a: Optional[str] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"$root.type": ["none"]}),
    )
    b: Optional[str] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"$root.type": ["none"]}),
    )
    c: Optional[str] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"$root.type": ["password"]}),
    )
    d: Optional[str] = Field(
        default=None,
        sa_column_kwargs=_conditional_props({"$root.type": ["password"]}),
    )


class RootControlledRecord(SQLModel, table=True):
    __tablename__ = "test_root_controlled_record"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    properties: RootControlledProperties = Field(sa_column=Column(JSON))


def test_conditional_json_rules_are_emitted_for_object_array_and_dict():
    result = get_model_fields(ConditionalJsonRecord, "conditional_json_record")
    fields = {field.name: field for field in result.fields}

    assert fields["value"].json_condition_schema is not None
    assert fields["values"].json_condition_schema is not None
    assert fields["values_by_key"].json_condition_schema is not None

    schema = fields["value"].json_model_schema
    assert schema is not None
    by_name = {field["name"]: field for field in schema["fields"]}
    assert by_name["data_type"]["default"] == "float"
    assert by_name["enum_values"]["visibleWhen"] == {"data_type": ["enum"]}
    assert by_name["enum_values"]["requiredWhen"] == {"data_type": ["enum"]}
    assert by_name["enum_values"]["clearWhenHidden"] is True
    assert by_name["min_value"]["visibleWhen"] == {"data_type": ["float", "int"]}

    model = _build_model_dict(
        "ConditionalJsonRecord", "conditional_json_record", "conditional_json_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template("schema.py.j2").render(model=model)

    assert '"container": "object"' in rendered
    assert '"container": "array"' in rendered
    assert '"container": "dict"' in rendered
    assert "def _normalize_conditional_json_values" in rendered
    assert rendered.count("def _normalize_conditional_json_fields") == 2
    compile(rendered, "generated_schema.py", "exec")


def test_root_field_controls_json_children_in_frontend_and_backend(monkeypatch):
    result = get_model_fields(RootControlledRecord, "root_controlled_record")
    properties = next(field for field in result.fields if field.name == "properties")
    schema = properties.json_model_schema
    assert schema is not None
    by_name = {field["name"]: field for field in schema["fields"]}
    assert by_name["a"]["visibleWhen"] == {"$root.type": ["none"]}
    assert by_name["c"]["visibleWhen"] == {"$root.type": ["password"]}

    model = _build_model_dict(
        "RootControlledRecord", "root_controlled_record", "root_controlled_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))
    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)
    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(model=model)
    rendered_schema = environment.get_template("schema.py.j2").render(model=model)

    assert "const rootValue = watch();" in create_page
    assert "rootValue={rootValue}" in create_page
    assert "rootValue={currentItem}" in detail_page
    assert "rootValue={editRootValue}" in detail_page

    app_module = types.ModuleType("app")
    models_module = types.ModuleType("app.models")
    source_module = types.ModuleType("app.models.root_controlled_record")
    source_module.RootControlledRecord = RootControlledRecord
    source_module.RootControlledProperties = RootControlledProperties
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.models", models_module)
    monkeypatch.setitem(sys.modules, "app.models.root_controlled_record", source_module)
    # Load the real shared schema authorization base into this isolated package.
    import importlib.util
    access_path = Path(__file__).parents[1] / "src/onesite/templates/backend/app/core/access.py"
    access_spec = importlib.util.spec_from_file_location("app.core.access", access_path)
    access = importlib.util.module_from_spec(access_spec)
    access_spec.loader.exec_module(access)
    monkeypatch.setitem(sys.modules, "app.core", types.ModuleType("app.core"))
    monkeypatch.setitem(sys.modules, "app.core.access", access)

    namespace: dict[str, object] = {}
    exec(compile(rendered_schema, "generated_schema.py", "exec"), namespace)

    create_schema = namespace["RootControlledRecordCreate"]
    none_value = create_schema(
        type="none", properties={"a": "a", "b": "b", "c": "stale", "d": "stale"}
    )
    assert none_value.properties.model_dump(exclude_none=True) == {"a": "a", "b": "b"}
    password_value = create_schema(
        type="password", properties={"a": "stale", "b": "stale", "c": "c", "d": "d"}
    )
    assert password_value.properties.model_dump(exclude_none=True) == {"c": "c", "d": "d"}


def test_root_condition_rejects_unknown_top_level_field():
    class InvalidProperties(SQLModel):
        value: Optional[str] = Field(
            default=None,
            sa_column_kwargs=_conditional_props({"$root.missing": ["yes"]}),
        )

    class InvalidRootRecord(SQLModel, table=True):
        __tablename__ = "test_invalid_root_record"
        id: Optional[int] = Field(default=None, primary_key=True)
        properties: InvalidProperties = Field(sa_column=Column(JSON))

    import pytest

    with pytest.raises(ValueError, match="unknown root field.*missing"):
        get_model_fields(InvalidRootRecord, "invalid_root_record")


def test_json_layout_compacts_rows_after_conditional_fields_are_hidden():
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

    assert "isJsonLayoutNodeVisible" in component
    assert "jsonLayoutColumns(visibleNodes)" in component
    assert "!matchesCondition(field.visibleWhen, v, rootValue)" in component
