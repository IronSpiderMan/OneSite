"""Shared Enum colors, field overrides, and per-value multi-select rendering."""
from enum import Enum, IntEnum

import pytest
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.metadata.colors import enum_color_config
from onesite.codegen.phases.introspect_models import _introspect_module
from test_read_fields_codegen import _template


class SharedStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    OTHER = "other"
    __onesite__ = {"color": {"active": "red", "closed": "green"}}


class Priority(IntEnum):
    LOW = 0
    HIGH = 1
    __onesite__ = {"color": {0: "blue", 1: "red"}}


class EnumColorRecord(SQLModel, table=True):
    __tablename__ = "test_enum_color_record"
    id: int | None = Field(default=None, primary_key=True)
    status: SharedStatus
    optional_status: SharedStatus | None = None
    statuses: list[SharedStatus] = Field(default_factory=list, sa_column=Column(JSON))
    overridden_statuses: list[SharedStatus] = Field(
        default_factory=list, sa_column=Column(JSON, info={"site_props": {
            "color": {"rules": [{"when": {"field": "priority", "eq": 1}, "color": "rose"}]}
        }}),
    )
    priority: Priority = Priority.LOW
    overridden: SharedStatus = Field(sa_column_kwargs={"info": {"site_props": {"color": "blue"}}})
    disabled: SharedStatus = Field(sa_column_kwargs={"info": {"site_props": {"color": None}}})
    conditional: SharedStatus = Field(sa_column_kwargs={"info": {"site_props": {
        "color": {"rules": [{"when": {"field": "priority", "eq": 1}, "color": "rose"}]}
    }}})


class OtherEnumColorRecord(SQLModel, table=True):
    __tablename__ = "test_other_enum_color_record"
    id: int | None = Field(default=None, primary_key=True)
    state: SharedStatus


def test_shared_colors_and_overrides():
    fields = {f.name: f for f in get_model_fields(EnumColorRecord).fields}
    for name in ("status", "optional_status", "statuses"):
        assert fields[name].color == {"rules": [
            {"when": {"field": name, "eq": "active"}, "color": "red"},
            {"when": {"field": name, "eq": "closed"}, "color": "green"},
        ]}
    assert fields["statuses"].color_each_value
    assert not fields["status"].color_each_value
    assert not fields["overridden_statuses"].color_each_value
    assert fields["overridden_statuses"].color["rules"][0]["when"]["field"] == "priority"
    assert fields["overridden"].color == "blue"
    assert fields["disabled"].color is None
    assert fields["conditional"].color == {"rules": [
        {"when": {"field": "priority", "eq": 1}, "color": "rose"}
    ]}
    assert fields["priority"].color["rules"][0]["when"]["eq"] == 0
    other = {f.name: f for f in get_model_fields(OtherEnumColorRecord).fields}
    assert other["state"].color["rules"][0]["when"]["field"] == "state"
    assert list(SharedStatus.__members__) == ["ACTIVE", "CLOSED", "OTHER"]


@pytest.mark.parametrize("mapping", ["red", {"ACTIVE": "red"}, {"missing": "red"}, {"active": "invalid"}, {"active": None}])
def test_rejects_invalid_enum_colors(mapping):
    original = SharedStatus.__onesite__
    try:
        SharedStatus.__onesite__ = {"color": mapping}
        with pytest.raises(ValueError, match=r"SharedStatus.__onesite__.color"):
            get_model_fields(EnumColorRecord)
    finally:
        SharedStatus.__onesite__ = original


def test_integer_keys_remain_typed():
    original = Priority.__onesite__
    try:
        Priority.__onesite__ = {"color": {"0": "red"}}
        with pytest.raises(ValueError, match="unknown enum value"):
            enum_color_config(Priority, field_name="priority")
    finally:
        Priority.__onesite__ = original


def test_unconfigured_and_empty_enum_colors():
    class Plain(str, Enum):
        A = "a"
    assert enum_color_config(Plain, field_name="value") is None
    Plain.__onesite__ = {"color": {}}
    assert enum_color_config(Plain, field_name="value") is None


def test_all_views_render_shared_and_multi_value_colors():
    model = _introspect_module(type("Module", (), {"EnumColorRecord": EnumColorRecord}), "enum_color_record")[0]
    for mode in ("list", "grid"):
        model["list_mode"] = mode
        page = _template("frontend_page_list.tsx.j2", model)
        assert 'field="status"' in page
        assert '"eq": "active"' in page
        assert '"statuses": value' in page
        assert '"overridden_statuses": value' not in page
        assert 'key={`${value}-${index}`}' in page
    page = _template("frontend_page_detail.tsx.j2", model)
    assert '"statuses": value' in page
    assert 'currentItem as unknown as Record<string, unknown>' in page
