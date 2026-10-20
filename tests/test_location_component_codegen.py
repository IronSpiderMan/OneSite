"""Regression coverage for the built-in geographic location component."""

from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import _inline_item_schema


class Location(SQLModel):
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class LocatedStore(SQLModel, table=True):
    __tablename__ = "test_located_store"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    location: Optional[Location] = Field(
        default=None,
        sa_column=Column(
            JSON,
            info={"site_props": {"component": "location"}},
        ),
    )


class InvalidLocatedStore(SQLModel, table=True):
    __tablename__ = "test_invalid_located_store"

    id: Optional[int] = Field(default=None, primary_key=True)
    location: Optional[str] = Field(
        default=None,
        sa_column=Column(
            JSON,
            info={"site_props": {"component": "location"}},
        ),
    )


def test_location_component_introspection_and_generated_forms():
    result = get_model_fields(LocatedStore, "located_store")
    model = _build_model_dict(
        "LocatedStore", "located_store", "located_store", result
    )
    field = next(field for field in result.fields if field.name == "location")

    assert field.type == "Optional[Location]"
    assert field.ui_type == "location"
    assert field.json_kind == "object"
    assert {item["name"] for item in field.json_model_schema["fields"]} == {
        "latitude",
        "longitude",
    }

    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    create_page = environment.get_template("frontend_page_create.tsx.j2").render(
        model=model
    )
    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(
        model=model
    )
    list_page = environment.get_template("frontend_page_list.tsx.j2").render(
        model=model
    )

    assert "import { LocationInput }" in create_page
    assert "<LocationInput value={value} onChange={onChange} />" in create_page
    assert "import { LocationInput }" in detail_page
    assert "<LocationInput value={value} onChange={onChange} />" in detail_page
    assert ".location.latitude}, ${item.location.longitude}" in list_page


def test_location_component_rejects_non_location_fields():
    with pytest.raises(ValueError, match="not an object field"):
        get_model_fields(InvalidLocatedStore, "invalid_located_store")


def test_bundled_location_model_and_browser_component_contract():
    template_root = Path(__file__).parents[1] / "src" / "onesite" / "templates"
    model_source = (template_root / "models" / "location.py").read_text()
    component_source = (
        template_root / "frontend" / "src" / "components" / "ui" / "location-input.tsx"
    ).read_text()

    assert "class Location(SQLModel):" in model_source
    assert "ge=-90, le=90" in model_source
    assert "ge=-180, le=180" in model_source
    assert "navigator.geolocation.getCurrentPosition" in component_source
    assert "enableHighAccuracy: true" in component_source
    assert "type=\"number\"" in component_source
    assert "MapContainer" in component_source
    assert "MapSelectionEvents" in component_source
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in component_source
    assert "VITE_MAP_TILE_URL" in component_source
    assert "map.invalidateSize()" in component_source
    assert "minHeight: '18rem'" in component_source
    assert "Choose on map" in component_source


def test_location_component_is_preserved_in_inline_relation_editors():
    result = get_model_fields(LocatedStore, "located_store")
    model = _build_model_dict(
        "LocatedStore", "located_store", "located_store", result
    )

    inline_fields, inline_schema = _inline_item_schema(model, excluded=set())
    location_field = next(
        field for field in inline_fields if field["name"] == "location"
    )
    location_ui_field = next(
        field for field in inline_schema["fields"] if field["name"] == "location"
    )

    assert location_field["type"] == "Dict[str, Any]"
    assert location_ui_field["kind"] == "location"

    component_source = (
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
    assert 'import { LocationInput } from "./location-input"' in component_source
    assert 'if (f.kind === "location")' in component_source
