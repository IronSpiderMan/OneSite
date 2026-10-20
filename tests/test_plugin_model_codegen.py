"""Regression coverage for plugin-owned generated models."""

from onesite.codegen.phases.plugin_models import phase_generate_plugin_models
from onesite.codegen.phases.introspect_models import phase_introspect
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.phases.sync_models import phase_sync_models


def test_site_logger_model_is_created_after_model_mirror_cleanup(tmp_path):
    backend = tmp_path / "generated" / "backend"
    generated_model = backend / "app" / "models" / "app_log.py"
    generated_model.parent.mkdir(parents=True)
    generated_model.write_text("stale plugin output\n", encoding="utf-8")

    phase_sync_models(tmp_path, backend)
    assert not generated_model.exists()

    phase_generate_plugin_models({"plugins": ["site_logger"]}, tmp_path, backend)

    assert generated_model.exists()
    assert "class AppLog" in generated_model.read_text(encoding="utf-8")


def test_project_app_log_model_overrides_plugin_default(tmp_path):
    source_model = tmp_path / "app" / "models" / "app_log.py"
    source_model.parent.mkdir(parents=True)
    source_model.write_text("PROJECT_MODEL = True\n", encoding="utf-8")
    backend = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models({"plugins": ["site_logger"]}, tmp_path, backend)

    generated_model = backend / "app" / "models" / "app_log.py"
    assert generated_model.read_text(encoding="utf-8") == "PROJECT_MODEL = True\n"


def test_device_timeseries_plugin_generates_six_models(tmp_path):
    backend = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models(
        {"plugins": ["device_timeseries"]}, tmp_path, backend
    )

    models = backend / "app" / "models"
    expected = {
        "device_model.py",
        "device_model_field.py",
        "device.py",
        "device_field.py",
        "device_history.py",
        "device_history_latest.py",
    }
    assert expected <= {path.name for path in models.glob("*.py")}
    assert '__tablename__ = "device_latest"' in (
        models / "device_history_latest.py"
    ).read_text(encoding="utf-8")
    assert '"latest_table": "device_latest"' in (
        models / "device_history.py"
    ).read_text(encoding="utf-8")


def test_project_model_can_override_one_device_timeseries_model(tmp_path):
    source_model = tmp_path / "app" / "models" / "device.py"
    source_model.parent.mkdir(parents=True)
    source_model.write_text("PROJECT_DEVICE = True\n", encoding="utf-8")
    backend = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models(
        {"plugins": ["device_timeseries"]}, tmp_path, backend
    )

    models = backend / "app" / "models"
    assert (models / "device.py").read_text(encoding="utf-8") == "PROJECT_DEVICE = True\n"
    assert (models / "device_model.py").exists()


def test_device_timeseries_models_import_and_resolve_as_one_schema(tmp_path):
    backend = tmp_path / "generated" / "backend"
    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models(
        {"plugins": ["device_timeseries"]}, tmp_path, backend
    )

    models = phase_introspect(backend)
    phase_resolve_relationships(models)
    by_name = {model["name"]: model for model in models}

    assert {
        "DeviceModel",
        "DeviceModelField",
        "Device",
        "DeviceField",
        "DeviceHistory",
        "DeviceLatest",
    } <= set(by_name)
    assert by_name["DeviceHistory"]["primary_key_columns"] == [
        "device_id", "metric", "reported_at"
    ]
    assert by_name["DeviceHistory"]["timescaledb_entity_field"] == "device_id"
    assert by_name["DeviceHistory"]["timescaledb_metric_field"] == "metric"
    assert by_name["DeviceHistory"]["timescaledb_metric_target_table"] == "device_field"
    assert by_name["DeviceHistory"]["timescaledb_metric_target_field"] == "name"
    assert by_name["DeviceHistory"]["timescaledb_latest_table_name"] == "device_latest"
    assert by_name["DeviceLatest"]["primary_key_columns"] == [
        "device_id", "metric"
    ]
    assert by_name["Device"]["id_type"] == "str"
    device_fields = {field["name"]: field for field in by_name["Device"]["fields"]}
    assert by_name["Device"]["primary_key_columns"] == ["id"]
    assert device_fields["id"]["permissions"] == "r"
    assert device_fields["id"]["required"] is False
    assert device_fields["name"]["is_unique"] is True
    assert by_name["DeviceField"]["primary_key_columns"] == ["device_id", "name"]
    assert by_name["DeviceField"]["uses_composite_identity"] is True
    assert "id" not in {field["name"] for field in by_name["DeviceField"]["fields"]}
    assert {field["name"] for field in by_name["Device"]["fields"]} == {
        "id", "name", "device_model_id", "protocol", "collection_interval_seconds",
        "timeout", "heartbeat_interval_seconds"
    }
    assert {
        field["name"] for field in by_name["DeviceField"]["fields"]
    } >= {
        "name",
        "dtype",
        "unit",
        "address",
        "attribute",
        "value",
        "report_mode",
        "deadband",
    }
    assert "heartbeat_interval_seconds" not in {
        field["name"] for field in by_name["DeviceField"]["fields"]
    }
    assert {field["name"] for field in by_name["DeviceHistory"]["fields"]} == {
        "device_id", "metric", "value", "reported_at"
    }
    assert {field["name"] for field in by_name["DeviceLatest"]["fields"]} == {
        "device_id", "metric", "value", "reported_at"
    }
    assert by_name["DeviceHistory"]["timescaledb_metric_label_field"] == "name"
    assert by_name["DeviceHistory"]["timescaledb_metric_data_type_field"] == "dtype"
    assert by_name["DeviceHistory"]["timescaledb_metric_unit_field"] == "unit"
    assert not any(by_name["DeviceModelField"]["role_visible"].values())
    assert not any(by_name["DeviceField"]["role_visible"].values())
    assert by_name["DeviceModelField"]["standalone"] is False
    assert by_name["DeviceField"]["standalone"] is False
    device_field_permissions = {
        field["name"]: field["permissions"]
        for field in by_name["DeviceField"]["fields"]
    }
    assert device_field_permissions["device_id"] == "r"
    assert device_field_permissions["device_model_field_id"] == "r"
    assert device_field_permissions["name"] == "r"
    assert any(
        relation["source_model"] == "DeviceModelField"
        and relation["editor"] == "embedded"
        for relation in by_name["DeviceModel"]["reverse_foreign_keys"]
    )
    assert any(
        relation["source_model"] == "DeviceField"
        and relation["editor"] == "embedded"
        and relation["allow_existing"] is False
        for relation in by_name["Device"]["reverse_foreign_keys"]
    )


    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    environment = Environment(loader=FileSystemLoader(
        Path(__file__).parents[1] / "src/onesite/templates/codegen"
    ))
    for model_name in ("Device", "DeviceField"):
        schema = environment.get_template("schema.py.j2").render(model=by_name[model_name])
        compile(schema, f"{model_name}_schema.py", "exec")
        if model_name == "Device":
            create_schema = schema.split("class DeviceCreate", 1)[1].split(
                "class DeviceUpdate", 1
            )[0]
            assert "    id:" not in create_schema
        else:
            update_schema = schema.split("class DeviceFieldUpdate", 1)[1]
            assert "value: Optional[str] = None" in update_schema
            assert by_name[model_name].override_fields[0]["write_handler"] == "persist_value"
