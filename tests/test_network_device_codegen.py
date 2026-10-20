"""Coverage for model-level network device reachability configuration."""

import asyncio
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.phases.introspect_models import _introspect_module
from onesite_runtime import (
    NetworkDeviceMetadata,
    ReadContext,
    probe_network_url,
    resolve_read_data,
)


class NetworkCamera(SQLModel, table=True):
    __tablename__ = "test_network_camera"
    __onesite__ = {
        "network_device": {
            "url_field": "endpoint",
            "status_field": "is_online",
            "timeout": 0.25,
        }
    }

    id: int | None = Field(default=None, primary_key=True)
    endpoint: str


class CustomDevice(SQLModel, table=True):
    __tablename__ = "test_custom_device"
    __onesite__ = {
        "network_device": {"url_field": "endpoint", "checker": "check_endpoint"}
    }

    id: int | None = Field(default=None, primary_key=True)
    endpoint: str

    async def check_endpoint(self, url, values) -> bool:
        return url == "vendor://ready" and values["id"] == self.id


def _model(model_class):
    models = _introspect_module(
        type("Module", (), {model_class.__name__: model_class}),
        model_class.__name__.lower(),
    )
    assert models is not None
    model = models[0]
    model.update(
        m2m_fields=[], reverse_m2m=[], reverse_definition_bindings=[],
        definition_binding_meta=None, is_timescaledb=False,
        is_notification_table=False,
    )
    return model


def _template(name: str, model) -> str:
    root = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(root)).get_template(name).render(model=model)


def test_network_device_injects_read_field_and_generated_probe():
    model = _model(NetworkCamera)

    assert model.network_device == {
        "url_field": "endpoint",
        "status_field": "is_online",
        "checker": None,
        "timeout": 0.25,
        "udp_payload": "",
    }
    status = next(field for field in model.extra_fields if field["name"] == "is_online")
    assert status["type"] == "bool"
    assert status["component"] == "online_status"
    assert model.has_read_resolvers is True
    assert model.network_probe_can_batch is True

    schema = _template("schema.py.j2", model)
    service = _template("service.py.j2", model)
    list_page = _template("frontend_page_list.tsx.j2", model)
    detail_page = _template("frontend_page_detail.tsx.j2", model)

    compile(schema, "generated_schema.py", "exec")
    compile(service, "generated_service.py", "exec")
    assert "is_online: bool" in schema
    assert 'url_field="endpoint"' in service
    assert "NetworkDeviceMetadata" in service
    assert "await asyncio.gather" in service
    assert "common.online" in list_page
    assert "common.offline" in detail_page


def test_custom_network_checker_resolves_boolean_status():
    device = CustomDevice(id=7, endpoint="vendor://ready")
    result = asyncio.run(
        resolve_read_data(
            device,
            device.model_dump(),
            ReadContext(session=object()),
            NetworkDeviceMetadata(url_field="endpoint", checker="check_endpoint"),
        )
    )
    assert result["online"] is True


def test_tcp_probe_uses_scheme_default_port_and_handles_connection_errors(monkeypatch):
    calls = []

    class Writer:
        def close(self):
            pass

        async def wait_closed(self):
            pass

    async def connected(host, port, **kwargs):
        calls.append((host, port, kwargs["ssl"] is not None))
        return object(), Writer()

    monkeypatch.setattr(asyncio, "open_connection", connected)
    assert asyncio.run(probe_network_url("mqtt://broker.local", timeout=0.2))
    assert calls == [("broker.local", 1883, False)]

    async def refused(*args, **kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr(asyncio, "open_connection", refused)
    assert not asyncio.run(probe_network_url("opc.tcp://plc.local", timeout=0.2))
    assert not asyncio.run(probe_network_url("vendor://device.local", timeout=0.2))


def test_network_device_rejects_invalid_field_and_checker():
    class InvalidDevice(SQLModel, table=True):
        __tablename__ = "test_invalid_network_device"
        __onesite__ = {"network_device": "missing"}
        id: int | None = Field(default=None, primary_key=True)
        endpoint: str

    with pytest.raises(ValueError, match="must name a readable model field"):
        _model(InvalidDevice)
