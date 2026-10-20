"""Kafka integration scaffolding and generated runtime coverage."""

import ast

import pytest

from onesite.codegen.assets import _sync_kafka_callbacks, sync_backend_assets
from onesite.codegen.config import SiteConfigError, validate_kafka_config
from onesite.codegen.envsync import sync_env_files


def _callbacks():
    return [
        {
            "topic": "nexus.telemetry",
            "handler": "on_heartbeat",
            "group_id": "onesite-edgeflow-health",
        }
    ]


def test_kafka_handler_is_scaffolded_and_bound(tmp_path):
    backend = tmp_path / "generated" / "backend"
    _sync_kafka_callbacks(tmp_path, backend, _callbacks())

    source = tmp_path / "app" / "integrations" / "kafka" / "on_heartbeat.py"
    generated = backend / "app" / "integrations" / "kafka" / "on_heartbeat.py"
    bindings = backend / "app" / "core" / "kafka_bindings.py"

    assert generated.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "async def on_heartbeat(topic: str, payload: bytes)" in source.read_text(encoding="utf-8")
    assert "app.integrations.kafka.on_heartbeat" in bindings.read_text(encoding="utf-8")
    assert "settings.KAFKA_CALLBACK_0_TOPIC" in bindings.read_text(encoding="utf-8")
    assert "group_id=settings.KAFKA_CALLBACK_0_GROUP_ID" in bindings.read_text(encoding="utf-8")


def test_kafka_handler_signature_is_validated(tmp_path):
    source_dir = tmp_path / "app" / "integrations" / "kafka"
    source_dir.mkdir(parents=True)
    (source_dir / "on_heartbeat.py").write_text(
        "async def on_heartbeat(payload: bytes):\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(SiteConfigError, match="parameters do not match"):
        _sync_kafka_callbacks(tmp_path, tmp_path / "generated" / "backend", _callbacks())


def test_kafka_callback_defaults_group_id():
    config = {
        "kafka": {
            "brokers": ["localhost:9092"],
            "callbacks": [{"topic": "events", "handler": "handle"}],
        }
    }
    validate_kafka_config(config)
    assert config["kafka"]["callbacks"][0]["group_id"] == "onesite_backend"


def test_kafka_parameters_are_synced_to_backend_env(tmp_path):
    backend = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    config = {
        "project_name": "Kafka Test",
        "database_url": "sqlite:///./app.db",
        "secret_key": "test",
        "allowed_origins": [],
        "kafka": {
            "brokers": ["kafka-1:9092", "kafka-2:9092"],
            "callbacks": _callbacks(),
        },
    }

    sync_env_files(config, backend, frontend)

    environment = (backend / ".env").read_text(encoding="utf-8")
    assert 'KAFKA_BROKERS=["kafka-1:9092", "kafka-2:9092"]' in environment
    assert "KAFKA_CALLBACK_0_TOPIC=nexus.telemetry" in environment
    assert (
        "KAFKA_CALLBACK_0_GROUP_ID=onesite-edgeflow-health" in environment
    )


def test_generated_kafka_runtime_main_and_requirements(tmp_path):
    config = {
        "project_name": "Kafka Test",
        "secret_key": "test",
        "access_token_expire_minutes": 60,
        "database_url": "sqlite:///./app.db",
        "allowed_origins": [],
        "upload_dir": "uploads",
        "extra": {"TIMEZONE": "Asia/Shanghai"},
        "kafka": {
            "brokers": ["wsl:9092"],
            "callbacks": _callbacks(),
        },
    }
    backend = tmp_path / "backend"
    sync_backend_assets(tmp_path, backend, config)

    for relative in (
        "app/main.py",
        "app/core/config.py",
        "app/core/kafka.py",
        "app/core/kafka_bindings.py",
    ):
        generated = backend / relative
        ast.parse(generated.read_text(encoding="utf-8"), filename=str(generated))

    assert "await kafka_manager.start()" in (backend / "app/main.py").read_text(encoding="utf-8")
    assert "await kafka_manager.stop()" in (backend / "app/main.py").read_text(encoding="utf-8")
    assert 'KAFKA_BROKERS: List[str] = ["wsl:9092"]' in (backend / "app/core/config.py").read_text(encoding="utf-8")
    generated_config = (backend / "app/core/config.py").read_text(encoding="utf-8")
    assert 'KAFKA_CALLBACK_0_TOPIC: str = "nexus.telemetry"' in generated_config
    assert (
        'KAFKA_CALLBACK_0_GROUP_ID: str = "onesite-edgeflow-health"'
        in generated_config
    )
    requirements = (backend / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "aiokafka" in requirements
    assert "python-snappy" in requirements

    dockerfile = (backend / "Dockerfile").read_text(encoding="utf-8")
    assert "libsnappy-dev" in dockerfile
    assert "libsnappy1v5" in dockerfile


def test_kafka_consumer_creation_is_retried_when_it_fails():
    """Connection setup errors must not end the background consumer task."""
    source = (
        "src/onesite/templates/codegen/kafka.py.j2"
    )
    module = ast.parse(open(source, encoding="utf-8").read())
    consume = next(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_consume_with_retry"
    )

    consumer_assignment = next(
        node
        for node in ast.walk(consume)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "AIOKafkaConsumer"
    )
    retry_try = next(node for node in consume.body if isinstance(node, ast.While)).body[1]

    assert isinstance(retry_try, ast.Try)
    assert consumer_assignment in retry_try.body
