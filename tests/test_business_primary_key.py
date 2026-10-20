"""Regression coverage for explicitly creatable business primary keys."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import (
    _build_model_dict,
    _process_introspected_class,
)


class Device(SQLModel, table=True):
    __tablename__ = "test_device"

    id: str = Field(
        primary_key=True,
        sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}},
    )
    name: str


class GeneratedIdModel(SQLModel, table=True):
    __tablename__ = "test_generated_id"

    id: Optional[int] = Field(default=None, primary_key=True)


class ExplicitTableNameModel(SQLModel, table=True):
    __tablename__ = "legacy_compact_table"

    id: int = Field(primary_key=True)


def _model():
    result = get_model_fields(Device, "device")
    return _build_model_dict("Device", "device", "device", result)


def test_business_primary_key_is_included_in_create_schema_and_read_schema():
    model = _model()
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    template = Environment(loader=FileSystemLoader(template_dir)).get_template("schema.py.j2")

    schema = template.render(model=model)

    assert model.id_type == "str"
    assert "class DeviceCreate(WriteModel):" in schema
    assert "    id: str" in schema
    assert "class DeviceRead(DeviceBase):\n    id: str" in schema


def test_business_primary_key_is_used_by_frontend_client():
    model = _model()
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    template = Environment(loader=FileSystemLoader(template_dir)).get_template("frontend_service.ts.j2")

    client = template.render(model=model)

    assert "id: string;" in client
    assert "getDevice = async (id: string)" in client
    assert "bulkDeleteDevice = async (ids: string[])" in client

    store_template = Environment(loader=FileSystemLoader(template_dir)).get_template("frontend_store.ts.j2")
    store = store_template.render(model=model)
    assert "fetchItem: (id: string)" in store
    assert "bulkDeleteItem: (ids: string[], options?: MutationOptions)" in store


def test_business_primary_key_is_used_by_api_paths():
    model = _model()
    model.update(
        min_role_for_read="USER",
        min_role_for_create="USER",
        min_role_for_update="USER",
        min_role_for_delete="USER",
        m2m_fields=[],
        reverse_m2m=[],
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    template = Environment(loader=FileSystemLoader(template_dir)).get_template("api.py.j2")

    api = template.render(model=model)

    assert "async def read_device(" in api
    assert "    id: str," in api
    assert "ids: Annotated[List[str], Body(embed=True)]" in api


def test_generated_primary_key_remains_a_concrete_integer_type():
    result = get_model_fields(GeneratedIdModel, "generated_id")
    model = _build_model_dict("GeneratedIdModel", "generated_id", "generated_id", result)

    assert model.id_type == "int"


def test_explicit_table_name_is_preserved_in_model_metadata():
    model = _process_introspected_class(
        ExplicitTableNameModel,
        "ExplicitTableNameModel",
        "explicit_table_name_model",
    )

    assert model is not None
    assert model["table_name"] == "legacy_compact_table"


def test_string_primary_key_is_used_by_timeseries_detail_helpers():
    model = _model()
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_foreign_keys=[],
        reverse_timeseries=[
            {
                "model_name": "DeviceMetric",
                "module_name": "device_metric",
                "metric_field": "metric",
                "time_field": "reported_at",
            }
        ],
        definition_binding_meta=None,
        actions={},
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    detail = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert "const fetchDeviceMetricRealtime = async (itemId: string)" in detail
    assert "const fetchDeviceMetricHistory = async (itemId: string)" in detail
    assert "fetchDeviceMetricHistory(itemId);" not in detail
    assert detail.count("fetchDeviceMetricHistory(id);") == 1
    assert "[id, DeviceMetricTimeRange, DeviceMetricCustomStartTime, DeviceMetricCustomEndTime]" in detail
    assert "const refreshDeviceMetricHistory = async (itemId: string)" in detail
    assert detail.count("let perMetric = false;") == 2
    assert detail.count("perMetric = true;") == 2
    assert detail.count(
        "getDeviceMetricHistory(itemId, undefined, startTime, endTime, limit, perMetric)"
    ) == 2


def test_timeseries_latest_panel_is_dense_and_searchable():
    model = _model()
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_foreign_keys=[],
        reverse_timeseries=[
            {
                "model_name": "DeviceMetric",
                "module_name": "device_metric",
                "metric_field": "metric",
                "time_field": "reported_at",
            }
        ],
        definition_binding_meta={
            "definition_fk": "device_model_id",
            "definitions_field": "properties",
            "config_field": None,
        },
        actions={},
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    detail = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert "DeviceMetricFilteredRealtime" in detail
    assert "setDeviceMetricRealtimeSearch" in detail
    assert "setDeviceMetricRealtimeDensity" in detail
    assert "xl:grid-cols-3 2xl:grid-cols-4" in detail
    assert "<AreaChart data={trendData}" in detail
    assert '<XAxis dataKey="time" hide />' in detail
    assert "new Date(point.time).toISOString()" in detail
    assert "labelFormatter={(timestamp)" not in detail
    assert "<Clock className=" in detail
    assert "DeviceMetric — History" not in detail
    assert "maximumFractionDigits: 6" in detail
    assert "borderLeft" not in detail


def test_metric_timeseries_uses_dense_hub_cards_without_definition_binding():
    model = _model()
    model.update(
        m2m_fields=[],
        reverse_m2m=[],
        reverse_foreign_keys=[],
        reverse_timeseries=[
            {
                "model_name": "DeviceMetric",
                "module_name": "device_metric",
                "metric_field": "device_field_id",
                "time_field": "reported_at",
            }
        ],
        definition_binding_meta=None,
        actions={},
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    detail = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert "DeviceMetricFilteredRealtime" in detail
    assert "xl:grid-cols-3 2xl:grid-cols-4" in detail
    assert "<AreaChart data={trendData}" in detail
    assert "DeviceMetric — History" not in detail
    assert "No realtime data." not in detail


def test_timeseries_service_uses_text_entity_id_type():
    model = _model()
    model.update(
        is_timescaledb=True,
        timescaledb_entity_sql_type="TEXT",
        timescaledb_metric_field="metric",
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    service = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_service.ts.j2"
    ).render(model=model)

    assert "getDeviceRealtime = async (entityId: string)" in service
    assert "entityId: string," in service
