"""Coverage for developer-defined Read-only response field resolvers."""

import asyncio
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from onesite.codegen.phases.introspect_models import _introspect_module
from onesite_runtime import (
    ReadContext,
    WriteContext,
    extra_field,
    override_field,
    resolve_read_data,
    resolve_write_data,
)


class ReadDecoratedRecord(SQLModel, table=True):
    __tablename__ = "test_read_decorated_record"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    quantity: int

    @extra_field(label={"en": "Summary"}, show_in_list=False)
    def summary(self, values) -> str:
        return f"{values['title']} ({self.quantity})"

    @override_field("title")
    async def present_title(self, value, current_user) -> str:
        suffix = "admin" if current_user == "admin" else "viewer"
        return f"{value} [{suffix}]"


def _model():
    models = _introspect_module(
        type("Module", (), {"ReadDecoratedRecord": ReadDecoratedRecord}),
        "read_decorated_record",
    )
    assert models is not None
    model = models[0]
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
    return model


def _template(name: str, model) -> str:
    root = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(root)).get_template(name).render(model=model)


def test_extra_and_override_metadata_are_extracted_and_rendered():
    model = _model()
    model["page_edit"] = True

    assert model.has_read_resolvers is True
    assert model.extra_fields == [{
        "name": "summary",
        "type": "str",
        "handler": "summary",
        "label": {"en": "Summary"},
        "show_in_list": False,
        "show_in_detail": True,
        "py_imports": [],
    }]
    assert model.override_fields == [{
        "field": "title",
        "handler": "present_title",
        "read_type": "str",
        "py_imports": [],
        "raw_field": "title__raw",
    }]

    schema = _template("schema.py.j2", model)
    service = _template("service.py.j2", model)
    api = _template("api.py.j2", model)
    frontend_service = _template("frontend_service.ts.j2", model)
    _template("frontend_page_list.tsx.j2", model)
    detail_page = _template("frontend_page_detail.tsx.j2", model)

    compile(schema, "generated_schema.py", "exec")
    compile(service, "generated_service.py", "exec")
    compile(api, "generated_api.py", "exec")
    assert "summary: str" in schema
    assert "title__raw: Optional[str] = None" in schema
    assert "summary" not in schema.split("class ReadDecoratedRecordCreate", 1)[1].split("class ReadDecoratedRecordUpdate", 1)[0]
    assert "resolve_read_data" in service
    assert "current_user=current_user" in api
    assert 'source="list"' in service
    assert "summary: string" in frontend_service
    assert "Additional information" in detail_page
    # A read-only override keeps its formatted value for display while edit
    # mode initializes the model-native control from the preserved raw value.
    assert "title__raw?: string" in frontend_service
    assert "delete updatePayload['title'];" not in detail_page
    assert "setEditValue('title', item.title__raw);" in detail_page


def test_read_resolvers_transform_a_copy_of_response_data():
    record = ReadDecoratedRecord(id=1, title="Widget", quantity=3)
    original = {"id": 1, "title": "Widget", "quantity": 3}

    resolved = asyncio.run(
        resolve_read_data(
            record,
            original,
            ReadContext(session=object(), current_user="admin", source="detail"),
        )
    )

    assert original == {"id": 1, "title": "Widget", "quantity": 3}
    assert record.title == "Widget"
    assert resolved == {
        "id": 1,
        "title": "Widget [admin]",
        "title__raw": "Widget",
        "quantity": 3,
        "summary": "Widget (3)",
    }


def test_union_read_route_passes_read_context_user():
    model = _model()
    model["union_key"] = ["title", "quantity"]

    service = _template("service.py.j2", model)
    api = _template("api.py.j2", model)

    compile(service, "generated_union_service.py", "exec")
    compile(api, "generated_union_api.py", "exec")
    assert 'source="union"' in service
    assert "current_user=current_user" in api


def test_override_rejects_identity_and_foreign_key_fields():
    class InvalidOverride(SQLModel, table=True):
        __tablename__ = "test_invalid_override"
        id: int | None = Field(default=None, primary_key=True)
        title: str

        @override_field("id")
        def hide_id(self, value) -> int:
            return value

    with pytest.raises(ValueError, match="cannot override identity"):
        _introspect_module(type("Module", (), {"InvalidOverride": InvalidOverride}), "invalid_override")


def test_bidirectional_override_normalizes_display_value_before_write():
    class BidirectionalRecord(SQLModel, table=True):
        __tablename__ = "test_bidirectional_override"

        id: int | None = Field(default=None, primary_key=True)
        title: str

        @override_field("title")
        def present_title(self, value) -> str:
            return f"{value} [display]"

        @override_field("title", direction="write")
        def persist_title(self, value, context) -> str:
            assert context.operation == "update"
            return value.removesuffix(" [display]")

    models = _introspect_module(
        type("Module", (), {"BidirectionalRecord": BidirectionalRecord}),
        "bidirectional_override",
    )
    assert models is not None
    assert models[0].override_fields == [{
        "field": "title",
        "handler": "present_title",
        "read_type": "str",
        "py_imports": [],
        "write_handler": "persist_title",
    }]

    record = BidirectionalRecord(id=1, title="Widget")
    normalized = asyncio.run(
        resolve_write_data(
            record,
            {"title": "Widget [display]"},
            WriteContext(session=object(), operation="update"),
        )
    )
    assert normalized == {"title": "Widget"}

    model = models[0]
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
        page_edit=True,
    )
    schema = _template("schema.py.j2", model)
    detail_page = _template("frontend_page_detail.tsx.j2", model)
    assert "title__raw" not in schema
    assert "title: Optional[str] = None" in schema.split("class BidirectionalRecordUpdate", 1)[1]
    assert "setEditValue('title', item.title);" in detail_page


def test_read_only_json_override_keeps_native_editor_value():
    class Condition(SQLModel):
        operator: str
        value: str

    class Rule(SQLModel, table=True):
        __tablename__ = "test_read_override_rule"

        id: int | None = Field(default=None, primary_key=True)
        conditions: list[Condition] = Field(default_factory=list, sa_column=Column(JSON))

        @override_field("conditions")
        def present_conditions(self, value) -> str:
            return "\n".join(f"{item.operator}{item.value}" for item in value)

    models = _introspect_module(type("Module", (), {"Rule": Rule}), "rule")
    assert models is not None
    model = models[0]
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
        page_edit=True,
    )

    schema = _template("schema.py.j2", model)
    detail_page = _template("frontend_page_detail.tsx.j2", model)
    assert "conditions__raw: Optional[List[Condition]] = None" in schema
    assert "setEditValue('conditions', item.conditions__raw);" in detail_page
    assert 'name="conditions"' in detail_page
    assert "JsonModelTableEditor" in detail_page
