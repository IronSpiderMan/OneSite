"""Regression coverage for JSON object-array previews in paginated list pages."""

from pathlib import Path

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields


def test_paginated_list_summarizes_json_object_arrays():
    source = (
        Path(__file__).parents[1]
        / "src/onesite/templates/codegen/frontend_page_list.tsx.j2"
    ).read_text(encoding="utf-8")

    assert "include 'frontend_json_preview.tsx.j2'" in source
    source += (Path(__file__).parents[1] / "src/onesite/templates/codegen/frontend_json_preview.tsx.j2").read_text()
    source += (Path(__file__).parents[1] / "src/onesite/templates/codegen/frontend_list_cell.tsx.j2").read_text()
    assert "const formatObjectItem" in source
    assert "`${index + 1}. ${itemStr}`" in source
    assert "formatObjectItem(item as Record<string, unknown>)" in source
    assert "const labelFor = (key: string): string" in source
    assert "t(field.labelKey" in source
    assert "[key: string]: unknown;" in source
    assert "schema={ {{ (field.json_model_schema or field.json_item_schema) | tojson }} }" in source
    assert "if (Array.isArray(parsedValue) && parsedValue.length === 0)" in source
    assert "{JSON.stringify(parsedValue, null, 2)}" in source


def test_multi_display_preserves_object_and_array_preview_schemas():
    class PreviewItem(SQLModel):
        title: str

    class PreviewRecord(SQLModel, table=True):
        __tablename__ = "test_json_preview_record"
        __onesite__ = {
            "multi_display": {"fields": ["value", "values"], "label_field": "name"},
        }

        id: int | None = Field(default=None, primary_key=True)
        name: str
        value: PreviewItem = Field(sa_column=Column(JSON))
        values: list[PreviewItem] = Field(sa_column=Column(JSON))

    result = get_model_fields(PreviewRecord, "preview_record")
    fields = {field.name: field for field in result.fields}
    display = {field["field"]: field for field in result.multi_display["fields"]}

    object_schema = display["value"]["json_model_schema"]
    array_schema = display["values"]["json_item_schema"]
    assert object_schema == fields["value"].json_model_schema
    assert array_schema == fields["values"].json_item_schema
    for schema in (object_schema, array_schema):
        assert schema["name"] == "PreviewItem"
        assert schema["fields"][0]["name"] == "title"
        assert schema["fields"][0]["kind"] == "str"
        assert schema["fields"][0]["labelKey"] == "json_models.preview_item.fields.title"
