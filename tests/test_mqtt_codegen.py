"""MQTT source scaffolding and generated binding coverage."""

import ast
import json

import pytest

from onesite.codegen.assets import _sync_mqtt_callbacks, sync_backend_assets
from onesite.codegen.config import SiteConfigError, validate_mqtt_config


def _callbacks():
    return [
        {
            "topic": "alarm-trigger/alarms/#",
            "handler": "on_alarm",
            "qos": 1,
        }
    ]


def test_missing_mqtt_handler_is_scaffolded_and_copied_to_backend(tmp_path):
    backend_path = tmp_path / "generated" / "backend"

    _sync_mqtt_callbacks(tmp_path, backend_path, _callbacks())

    source = tmp_path / "app" / "integrations" / "mqtt" / "on_alarm.py"
    generated = (
        backend_path / "app" / "integrations" / "mqtt" / "on_alarm.py"
    )
    bindings = backend_path / "app" / "core" / "mqtt_bindings.py"

    assert source.exists()
    assert generated.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "async def on_alarm" in source.read_text(encoding="utf-8")
    assert "app.integrations.mqtt.on_alarm" in bindings.read_text(encoding="utf-8")
    assert '"alarm-trigger/alarms/#"' in bindings.read_text(encoding="utf-8")


def test_existing_mqtt_source_overwrites_generated_copy(tmp_path):
    source_dir = tmp_path / "app" / "integrations" / "mqtt"
    source_dir.mkdir(parents=True)
    source_code = (
        "async def on_alarm(topic: str, payload: str):\n"
        "    return {'handled': payload}\n"
    )
    (source_dir / "on_alarm.py").write_text(source_code, encoding="utf-8")

    generated = (
        tmp_path
        / "generated"
        / "backend"
        / "app"
        / "integrations"
        / "mqtt"
        / "on_alarm.py"
    )
    generated.parent.mkdir(parents=True)
    generated.write_text("# stale backend edit\n", encoding="utf-8")

    _sync_mqtt_callbacks(tmp_path, tmp_path / "generated" / "backend", _callbacks())

    assert generated.read_text(encoding="utf-8") == source_code


def test_mqtt_handler_must_be_a_top_level_async_function(tmp_path):
    source_dir = tmp_path / "app" / "integrations" / "mqtt"
    source_dir.mkdir(parents=True)
    (source_dir / "on_alarm.py").write_text(
        "def on_alarm(topic: str, payload: str):\n"
        "    return None\n",
        encoding="utf-8",
    )

    with pytest.raises(SiteConfigError, match="top-level async function"):
        _sync_mqtt_callbacks(tmp_path, tmp_path / "generated" / "backend", _callbacks())


@pytest.mark.parametrize(
    ("mqtt", "message"),
    [
        ({"callbacks": {}}, "must be a JSON array"),
        (
            {"callbacks": [{"topic": "devices/#", "handler": "../../main"}]},
            "valid Python identifier",
        ),
        (
            {"callbacks": [{"topic": "devices/#", "handler": "class"}]},
            "valid Python identifier",
        ),
        (
            {
                "callbacks": [
                    {"topic": "devices/#", "handler": "handle", "qos": 3}
                ]
            },
            "qos must be 0, 1, or 2",
        ),
    ],
)
def test_invalid_mqtt_callback_config_is_rejected(mqtt, message):
    config = json.loads(json.dumps({"mqtt": mqtt}))

    with pytest.raises(SiteConfigError, match=message):
        validate_mqtt_config(config)


def test_mqtt_callback_qos_defaults_to_one():
    config = {
        "mqtt": {
            "callbacks": [{"topic": "devices/#", "handler": "handle"}]
        }
    }

    validate_mqtt_config(config)

    assert config["mqtt"]["callbacks"][0]["qos"] == 1


def test_generated_mqtt_runtime_and_main_are_valid_python(tmp_path):
    config = {
        "project_name": "MQTT Test",
        "secret_key": "test",
        "access_token_expire_minutes": 60,
        "database_url": "sqlite:///./app.db",
        "allowed_origins": [],
        "upload_dir": "uploads",
        "extra": {"TIMEZONE": "Asia/Shanghai"},
        "mqtt": {
            "url": "mqtt://localhost:1883",
            "callbacks": _callbacks(),
        },
    }
    backend_path = tmp_path / "backend"

    sync_backend_assets(tmp_path, backend_path, config)

    for relative in (
        "app/main.py",
        "app/core/mqtt.py",
        "app/core/mqtt_bindings.py",
    ):
        generated = backend_path / relative
        ast.parse(generated.read_text(encoding="utf-8"), filename=str(generated))

    main_source = (backend_path / "app/main.py").read_text(encoding="utf-8")
    mqtt_source = (backend_path / "app/core/mqtt.py").read_text(encoding="utf-8")
    assert "await mqtt_manager.start()" in main_source
    assert "await mqtt_manager.connect()" not in main_source
    assert "async def _connect_with_retry" in mqtt_source
    assert "backend will continue and retry" in mqtt_source


def test_mqtt_source_uses_app_directory_in_modern_projects(tmp_path):
    (tmp_path / "app").mkdir()
    backend_path = tmp_path / "generated" / "backend"

    _sync_mqtt_callbacks(tmp_path, backend_path, _callbacks())

    assert (tmp_path / "app" / "integrations" / "mqtt" / "on_alarm.py").exists()
    assert (
        backend_path / "app" / "integrations" / "mqtt" / "on_alarm.py"
    ).exists()
    assert not (tmp_path / "integrations").exists()
