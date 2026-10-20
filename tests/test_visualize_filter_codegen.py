"""Regression coverage for typed visualize-filter comparisons."""

from enum import Enum
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.generate import _resolve_visualize_filters
from onesite.codegen.phases.introspect_models import _build_model_dict


class AlarmLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"


class NotificationRecord(SQLModel, table=True):
    __tablename__ = "test_notification_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: Optional[int] = None
    level: Optional[AlarmLevel] = None


class Category(SQLModel, table=True):
    __tablename__ = "test_category"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str


def _definition(model_class, name: str, module_name: str):
    result = get_model_fields(model_class, module_name)
    return _build_model_dict(
        name,
        module_name,
        module_name,
        result,
    )


def _model():
    model = _definition(NotificationRecord, "NotificationRecord", "notification_record")
    category = _definition(Category, "Category", "category")
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_definition_bindings=[],
        definition_binding_meta=None,
        is_timescaledb=False,
        is_notification_table=False,
        visualize={
            "show": True,
            "label_field": "level",
            "value_field": "id",
            "aggregation": "count",
            "time_field": None,
            "filters": [
                {
                    "model": "category",
                    "label_field": "title",
                    "path": "",
                    "filter_field": "category_id",
                },
                {"type": "enum", "field": "level"},
            ],
        },
    )
    lookup = {
        model["name"]: model,
        model["table_name"]: model,
        category["name"]: category,
        category["table_name"]: category,
    }
    _resolve_visualize_filters(model, lookup)
    return model


def test_visualize_filter_uses_mapped_column_instead_of_untyped_text():
    model = _model()
    category_filter, enum_filter = model["visualize"]["resolved_filters"]

    assert category_filter["owner_model_class"] == "NotificationRecord"
    assert category_filter["owner_source_module"] == "notification_record"
    assert enum_filter["owner_model_class"] == "NotificationRecord"
    assert enum_filter["owner_source_module"] == "notification_record"

    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    service = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "service.py.j2"
    ).render(model=model)

    compile(service, "generated_service.py", "exec")
    assert "_typed_filter_expression(NotificationRecord.category_id, _filter_val)" in service
    assert "_typed_filter_expression(NotificationRecord.level, _filter_val)" in service
    assert 'text(\'"test_notification_record".category_id = :' not in service
    assert 'text(\'"test_notification_record".level = :' not in service


def _fk_filter_models(source_table: str, target_table: str):
    target = {
        "name": "Category",
        "module_name": "category",
        "source_module": "category",
        "table_name": target_table,
        "fields": [{"name": "id"}, {"name": "title"}],
        "foreign_keys": [],
    }
    source = {
        "name": "Record",
        "module_name": "record",
        "source_module": "record",
        "table_name": source_table,
        "fields": [{"name": "category_id"}],
        "foreign_keys": [
            {"name": "category_id", "target_model": "Category"},
        ],
        "visualize": {
            "filters": [
                {
                    "model": "Category",
                    "path": "Category",
                    "filter_field": "id",
                    "label_field": "title",
                }
            ]
        },
    }
    lookup = {
        source["name"]: source,
        source["table_name"]: source,
        target["name"]: target,
        target["table_name"]: target,
    }
    return source, lookup


def test_visualize_filter_resolution_has_no_cross_call_global_state():
    first, first_lookup = _fk_filter_models("record_one", "category_one")
    second, second_lookup = _fk_filter_models("record_two", "category_two")

    _resolve_visualize_filters(first, first_lookup)
    _resolve_visualize_filters(second, second_lookup)

    first_join = first["visualize"]["resolved_filters"][0]["joins"][0]
    second_join = second["visualize"]["resolved_filters"][0]["joins"][0]
    assert first_join["to_table"] == "category_one"
    assert second_join["to_table"] == "category_two"
