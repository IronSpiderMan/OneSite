"""Regression coverage for TimescaleDB model metadata and latest-row sync."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.model_tables import _scan_timeseries
from onesite.codegen.phases.relationships import _resolve_timescaledb_metadata


class TimescaleSensor(SQLModel, table=True):
    __tablename__ = "test_timescale_sensor"

    id: int = Field(primary_key=True)


class TimescaleReading(SQLModel, table=True):
    __tablename__ = "test_timescale_reading"
    __onesite__ = {
        "time_series_table": {
            "entity_field": "sensor_id",
            "metric_field": "metric",
            "time_field": "observed_at",
        }
    }

    sensor_id: int = Field(
        foreign_key="test_timescale_sensor.id", primary_key=True
    )
    metric: str = Field(primary_key=True)
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), primary_key=True
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    value: float


class TimescaleInvalidReading(SQLModel, table=True):
    __tablename__ = "test_timescale_invalid_reading"
    __onesite__ = {
        "time_series_table": {
            "entity_field": "sensor_id",
            "time_field": "sequence",
        }
    }

    sensor_id: int = Field(
        foreign_key="test_timescale_sensor.id", primary_key=True
    )
    sequence: int = Field(primary_key=True)


def test_explicit_time_field_flows_to_resolved_timescale_metadata():
    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )

    _resolve_timescaledb_metadata([model])

    assert result.timescaledb_time_field == "observed_at"
    assert model.timescaledb_time_field == "observed_at"
    assert model.timescaledb_time_column == "observed_at"


def test_explicit_time_field_must_be_a_datetime_field():
    with pytest.raises(ValueError, match="time_field 'sequence' must be a datetime field"):
        get_model_fields(TimescaleInvalidReading, "timescale_invalid_reading")


def test_source_scanner_reads_dict_and_typed_time_series_configs(tmp_path):
    (tmp_path / "dict_reading.py").write_text(
        '''
class DictReading(SQLModel, table=True):
    __onesite__ = {"time_series_table": {
        "entity_field": "sensor_id", "time_field": "observed_at"
    }}
    observed_at: datetime
''',
        encoding="utf-8",
    )
    (tmp_path / "typed_reading.py").write_text(
        '''
class TypedReading(SQLModel, table=True):
    __onesite__ = OneSiteConfig(time_series_table=TimeSeriesTableConfig(
        entity_field="device_id", metric_field="metric", time_field="captured_at"
    ))
    captured_at: datetime
''',
        encoding="utf-8",
    )

    entries = {entry["source_file"]: entry for entry in _scan_timeseries(tmp_path)}

    assert entries["dict_reading"]["time_column"] == "observed_at"
    assert entries["typed_reading"]["entity_field"] == "device_id"
    assert entries["typed_reading"]["metric_field"] == "metric"
    assert entries["typed_reading"]["time_column"] == "captured_at"


def test_custom_latest_table_name_flows_to_metadata_and_generated_model(tmp_path):
    (tmp_path / "reading.py").write_text(
        '''
class Reading(SQLModel, table=True):
    __onesite__ = {"time_series_table": {
        "entity_field": "sensor_id", "latest_table": "sensor_latest"
    }}
    reported_at: datetime
''',
        encoding="utf-8",
    )
    entry = _scan_timeseries(tmp_path)[0]
    assert entry["latest_table"] == "sensor_latest"

    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )
    model["site_props"] = deepcopy(model["site_props"])
    model["site_props"]["time_series_table"]["latest_table"] = "sensor_latest"
    _resolve_timescaledb_metadata([model])
    assert model["timescaledb_latest_table_name"] == "sensor_latest"


def test_custom_latest_table_name_rejects_unsafe_identifier():
    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )
    model["site_props"] = deepcopy(model["site_props"])
    model["site_props"]["time_series_table"]["latest_table"] = "latest;drop table x"

    with pytest.raises(ValueError, match="must be a valid SQL identifier"):
        _resolve_timescaledb_metadata([model])


def test_removed_timeseries_definition_options_are_rejected():
    class CoupledReading(SQLModel, table=True):
        __tablename__ = "test_coupled_reading"
        __onesite__ = {
            "time_series_table": {
                "entity_field": "sensor_id",
                "model_table": "sensor_model",
            }
        }

        sensor_id: int = Field(foreign_key="test_timescale_sensor.id", primary_key=True)
        observed_at: datetime = Field(primary_key=True)

    with pytest.raises(ValueError, match="Removed time_series_table configuration"):
        get_model_fields(CoupledReading, "coupled_reading")


def test_timescale_lifecycle_is_explicit_and_normalized():
    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )
    model["site_props"]["time_series_table"]["lifecycle"] = {
        "chunk_interval": "1 day",
        "compress_after": "7 days",
        "retention_after": "90 days",
        "continuous_aggregate": True,
        "refresh_start_offset": "90 days",
    }

    _resolve_timescaledb_metadata([model])

    assert model["timescaledb_lifecycle"] == {
        "chunk_interval": "1 day",
        "compress_after": "7 days",
        "retention_after": "90 days",
        "bucket_interval": "1 hour",
        "refresh_start_offset": "90 days",
        "refresh_end_offset": "1 hour",
        "refresh_schedule_interval": "1 hour",
    }


def test_timescale_lifecycle_rejects_unsafe_interval():
    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )
    model["site_props"]["time_series_table"]["lifecycle"] = {
        "retention_after": "90 days'); DROP TABLE device; --"
    }

    with pytest.raises(ValueError, match="positive PostgreSQL interval"):
        _resolve_timescaledb_metadata([model])


def test_realtime_api_preserves_string_entity_ids():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    model = {
        "role_permissions": {"user":"crud", "admin":"crud", "developer":"crud"},
        "is_timescaledb": True,
        "lower_name": "reading",
        "timescaledb_entity_model": "Device",
        "timescaledb_entity_sql_type": "TEXT",
        "timescaledb_metric_field": "metric",
        "id_type": "str",
    }
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "api.py.j2"
    ).render(model=model)

    assert 'return {"data": results}' in rendered
    assert "DeviceModel" not in rendered
    assert "eid = int(entity_id)" not in rendered


def test_history_limit_can_be_applied_independently_per_metric():
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    result = get_model_fields(TimescaleReading, "timescale_reading")
    model = _build_model_dict(
        "TimescaleReading", "timescale_reading", "timescale_reading", result
    )
    model["site_props"]["time_series_table"]["lifecycle"] = {}
    _resolve_timescaledb_metadata([model])

    crud = environment.get_template("crud.py.j2").render(
        model=model,
        is_postgresql=True,
    )
    service = environment.get_template("service.py.j2").render(model=model)
    frontend = environment.get_template("frontend_service.ts.j2").render(model=model)

    compile(crud, "generated_crud.py", "exec")
    compile(service, "generated_service.py", "exec")
    assert "per_metric: bool = False" in crud
    assert "CROSS JOIN LATERAL" in crud
    assert "FROM timescale_reading_latest AS latest_metric" in crud
    assert "LIMIT :limit" in crud
    assert "per_metric=per_metric" in service
    assert "perMetric: boolean = false" in frontend
    assert "&per_metric=true" in frontend
