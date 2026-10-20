"""Regression coverage for JSON array rendering on generated detail pages."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class JsonEntry(BaseModel):
    name: str
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JsonDetailRecord(SQLModel, table=True):
    __tablename__ = "test_json_detail_record"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    entries: List[JsonEntry] = Field(default_factory=list, sa_column=Column(JSON))
    untyped_entries: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    keyed_entries: Dict[str, JsonEntry] = Field(default_factory=dict, sa_column=Column(JSON))
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


def test_json_arrays_render_as_related_style_tabs_and_tables():
    result = get_model_fields(JsonDetailRecord, "json_detail_record")
    model = _build_model_dict(
        "JsonDetailRecord", "json_detail_record", "json_detail_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    entries = next(field for field in result.fields if field.name == "entries")
    settings = next(field for field in result.fields if field.name == "settings")
    keyed_entries = next(field for field in result.fields if field.name == "keyed_entries")
    assert entries.json_kind == "array"
    assert settings.json_kind == "object"

    assert "activeTab === 'json-array-entries'" in detail_page
    assert "activeTab === 'json-array-untyped_entries'" in detail_page
    assert (
        "<TableHead>{t('json_models.json_entry.fields.name')}</TableHead>"
        in detail_page
    )
    assert (
        "<TableHead>{t('json_models.json_entry.fields.enabled')}</TableHead>"
        in detail_page
    )
    assert "<TableHead>name</TableHead>" not in detail_page
    assert "<TableHead>enabled</TableHead>" not in detail_page
    assert "items.flatMap((item: unknown)" in detail_page
    assert '<JsonModelTableEditor\n                                        collectionKind="array"' in detail_page
    assert '<JsonDynamicTableEditor collectionKind="array"' in detail_page
    assert "JSON.stringify(currentItem.entries, null, 2)" not in detail_page
    assert "activeTab === 'json-dict-keyed_entries'" in detail_page
    assert "activeTab === 'json-dict-settings'" in detail_page
    assert "Object.entries(currentItem.keyed_entries as Record<string, any>)" in detail_page
    assert "Object.entries(currentItem.settings as Record<string, any>)" in detail_page
    assert '<JsonModelTableEditor\n                                        collectionKind="dict"' in detail_page
    assert '<JsonDynamicTableEditor collectionKind="dict"' in detail_page
    assert "JSON.stringify(currentItem.settings, null, 2)" not in detail_page
    assert model.json_array_fields == [entries, next(field for field in result.fields if field.name == "untyped_entries")]
    assert model.json_dict_fields == [keyed_entries, settings]


def test_typed_json_dicts_use_inline_tables_in_create_forms():
    result = get_model_fields(JsonDetailRecord, "json_detail_record")
    model = _build_model_dict(
        "JsonDetailRecord", "json_detail_record", "json_detail_record", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)
    assert '<JsonModelTableEditor\n' in create_page
    assert 'collectionKind="dict"' in create_page
    assert "JsonModelDictEditor" not in create_page

    model.page_edit = False
    model.edit_mode = "modal"
    list_page = environment.get_template("frontend_page_list.tsx.j2").render(model=model)
    assert '<JsonModelTableEditor\n' in list_page
    assert 'collectionKind="dict"' in list_page
    assert "JsonModelDictEditor" not in list_page
