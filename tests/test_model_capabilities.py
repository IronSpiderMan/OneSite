import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from sqlmodel import Field, SQLModel

from onesite.codegen.capabilities import compile_capabilities
from onesite.generator import generate_code


class MappedServer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str
    username: str | None = None
    secret: str | None = None


def test_field_mapping_uses_same_name_defaults_and_rejects_invalid_overrides():
    config = {"kind": "opcua_server", "field_map": {"endpoint": "url", "password": "secret"}}
    assert compile_capabilities(MappedServer, [config])[0]["fields"] == {
        "endpoint": "url", "username": "username", "password": "secret",
    }
    for field_map, error in [
        ({"endpont": "url"}, "unknown fields: endpont"),
        ({"endpoint": "missing"}, "'missing' does not exist"),
        ({"endpoint": "id"}, "'id' is reserved"),
    ]:
        with pytest.raises(ValueError, match=error):
            compile_capabilities(MappedServer, [{**config, "field_map": field_map}])
    with pytest.raises(ValueError, match="declared more than once"):
        compile_capabilities(MappedServer, [config, config])


def test_database_requires_driver_enum():
    class InvalidDatabase(SQLModel, table=True):
        id: int | None = Field(default=None, primary_key=True)
        host: str
        port: int
        username: str
        password: str
        database: str
        driver: str

    with pytest.raises(ValueError, match="driver: 'driver' must be a string enum"):
        compile_capabilities(InvalidDatabase, [{"kind": "database"}])


@pytest.fixture
def generated(tmp_path, monkeypatch):
    source = tmp_path / "app/models"
    source.mkdir(parents=True)
    (tmp_path / "site_config.py").write_text('from onesite.config import SiteConfig\nconfig = SiteConfig(style="industrial")\n')
    (source / "connections.py").write_text(textwrap.dedent('''
        from enum import Enum
        from onesite.config import CapabilityConfig, CapabilityKind, OneSiteConfig
        from sqlmodel import Field, SQLModel

        class Gateway(SQLModel, table=True):
            __onesite__ = OneSiteConfig(
                owner_field="owner_id",
                capabilities=[CapabilityConfig(
                    kind=CapabilityKind.OPCUA_SERVER,
                    field_map={"endpoint": "address", "password": "credential"},
                    permissions={"browse": ["user", "admin"]},
                ), CapabilityConfig(
                    kind=CapabilityKind.MQTT_BROKER,
                    field_map={"endpoint": "broker_url", "password": "credential"},
                )],
            )
            id: str = Field(primary_key=True, sa_column_kwargs={"info": {"site_props": {"permissions": "rc"}}})
            owner_id: int = Field(foreign_key="user.id")
            name: str
            address: str
            broker_url: str
            username: str | None = None
            credential: str | None = None

        class Driver(str, Enum):
            POSTGRESQL = "postgresql"

        class Warehouse(SQLModel, table=True):
            __onesite__ = {"capabilities": [{"kind": "database"}]}
            id: int | None = Field(default=None, primary_key=True)
            host: str
            port: int = 5432
            username: str
            password: str
            database: str
            driver: Driver = Driver.POSTGRESQL
    '''))
    monkeypatch.chdir(tmp_path)
    generate_code()
    return tmp_path / "generated"


def test_all_capabilities_are_generated(generated):
    frontend = generated / "frontend/src"
    backend = generated / "backend"
    assert "/gateways/:id/mqtt" in (frontend / "Routes.tsx").read_text()
    assert "<OpcuaCapability" in (frontend / "pages/gateway/detail.tsx").read_text()
    assert "<DatabaseCapability" in (frontend / "pages/warehouse/detail.tsx").read_text()
    assert 'type="password"' in (frontend / "pages/gateway/index.tsx").read_text()
    requirements = (backend / "requirements.txt").read_text()
    assert "asyncua" in requirements and "gmqtt" in requirements
    assert not (backend / "app/api/endpoints/opcua_browse.py").exists()
    assert "onesite.config" not in (backend / "app/models/connections.py").read_text()


def test_generated_credentials_and_record_operation_permissions(generated, monkeypatch):
    monkeypatch.setenv("CAPABILITY_SECRET_KEY", "runtime-test-key-only-000000000000000")
    scenario = Path(__file__).resolve().parent / "support/capability_scenario.py"
    result = subprocess.run(
        [sys.executable, "-c", scenario.read_text()], cwd=generated / "backend",
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
