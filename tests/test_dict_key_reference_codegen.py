"""Codegen coverage for logical references to keys in JSON dictionaries."""

import ast
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Column, Field, JSON, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.config import DictKeyReferenceConfig, OneSiteConfig


class DictKeyProperty(SQLModel):
    label: str
    unit: str | None = None


class DictKeyOwner(SQLModel, table=True):
    __tablename__ = "dict_key_owner"

    id: int | None = Field(default=None, primary_key=True)
    properties: dict[str, DictKeyProperty] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )


class DictKeyReading(SQLModel, table=True):
    __tablename__ = "dict_key_reading"
    __onesite__ = OneSiteConfig(
        dict_key_references={
            "property_name": DictKeyReferenceConfig(
                owner_fk="owner_id",
                source_field="properties",
                display_field="label",
            )
        }
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="dict_key_owner.id")
    property_name: str
    value: float


def _models():
    definitions = []
    for model_class, module in (
        (DictKeyOwner, "dict_key_owner"),
        (DictKeyReading, "dict_key_reading"),
    ):
        result = get_model_fields(model_class, module)
        definitions.append(
            _build_model_dict(model_class.__name__, module, module, result)
        )
    phase_resolve_relationships(definitions)
    return {model.name: model for model in definitions}


def _template(name: str):
    directory = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(directory)).get_template(name)


def test_dict_key_reference_is_resolved_from_fk_and_json_annotations():
    models = _models()
    reading = models["DictKeyReading"]
    owner = models["DictKeyOwner"]

    assert reading.dict_key_reference_meta == [
        {
            "field": "property_name",
            "owner_fk": "owner_id",
            "owner_model": "DictKeyOwner",
            "owner_module": "dict_key_owner",
            "owner_id_type": "int",
            "owner_field": None,
            "source_field": "properties",
            "value_model": "DictKeyProperty",
            "display_field": "label",
            "on_source_change": "restrict",
        }
    ]
    property_field = next(field for field in reading.fields if field.name == "property_name")
    assert property_field.dict_key_reference["source_field"] == "properties"
    assert owner.reverse_dict_key_references[0]["source_model"] == "DictKeyReading"


def test_dict_key_reference_generates_validation_options_and_restrict_guard():
    models = _models()
    reading = models["DictKeyReading"]
    owner = models["DictKeyOwner"]

    reading_crud = _template("crud.py.j2").render(model=reading)
    reading_api = _template("api.py.j2").render(model=reading)
    owner_crud = _template("crud.py.j2").render(model=owner)

    ast.parse(reading_crud)
    ast.parse(reading_api)
    ast.parse(owner_crud)
    assert "async def _validate_dict_key_references(" in reading_crud
    assert "if reference_key not in source:" in reading_crud
    assert 'await _validate_dict_key_references(session, obj_data, db_obj)' in reading_crud
    assert '@router.get("/dict-key-options/property_name")' in reading_api
    assert 'options.append({"value": key, "label": str(label or key)})' in reading_api
    assert "Cannot remove properties key(s)" in owner_crud
    assert "DictKeyReading.property_name" in owner_crud


def test_dict_key_reference_generates_dependent_frontend_selects():
    reading = _models()["DictKeyReading"]

    service = _template("frontend_service.ts.j2").render(model=reading)
    create_page = _template("frontend_page_create.tsx.j2").render(model=reading)
    reading.page_edit = True
    detail_page = _template("frontend_page_detail.tsx.j2").render(model=reading)
    reading.page_edit = False
    list_page = _template("frontend_page_list.tsx.j2").render(model=reading)

    assert "getDictKeyReadingPropertyNameKeyOptions" in service
    assert "/dict-key-options/property_name" in service
    assert "disabled={!rootValue?.owner_id}" in create_page
    assert "setValue('property_name', '');" in create_page
    assert "disabled={!editRootValue?.owner_id}" in detail_page
    assert "disabled={!rootValue?.owner_id}" in list_page


def test_dict_key_reference_rejects_an_unknown_display_field():
    reading = _models()["DictKeyReading"]
    owner = _models()["DictKeyOwner"]
    reading.dict_key_references = {
        "property_name": {
            "owner_fk": "owner_id",
            "source_field": "properties",
            "display_field": "missing",
        }
    }

    with pytest.raises(ValueError, match="display_field 'missing'"):
        phase_resolve_relationships([owner, reading])


def test_searchable_select_falls_back_to_the_existing_value_as_its_label():
    component = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
        / "searchable-select.tsx"
    ).read_text(encoding="utf-8")

    assert "|| String(value)" in component
    assert "if (selectedLabel !== nextLabel)" in component
