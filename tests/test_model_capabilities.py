import subprocess
import sys
import textwrap
from copy import deepcopy
from enum import Enum
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


class Protocol(str, Enum):
    MQTT = "mqtt"
    OPCUA = "opcua"
    OPC_ALIAS = "opc_alias"
    PG = "pg"


class DatabaseDriver(str, Enum):
    POSTGRESQL = "postgresql"


class UniversalProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    protocol: Protocol
    endpoint: str | None = None
    username: str | None = None
    password: str | None = None
    opcua_url: str | None = None
    opcua_password: str | None = None
    host: str | None = None
    port: int = 5432
    database: str | None = None
    driver: DatabaseDriver = DatabaseDriver.POSTGRESQL


UNIVERSAL_CONFIG = {
    "kind": "universal",
    "selector_field": "protocol",
    "branches": {
        "mqtt": {"kind": "mqtt_broker", "permissions": {"subscribe": ["user", "admin"]}},
        "opc": {
            "kind": "opcua_server",
            "when": {"protocol": ["opcua", "opc_alias"]},
            "field_map": {"endpoint": "opcua_url", "password": "opcua_password"},
            "permissions": {"browse": ["user", "admin"]},
        },
        "pg": {"kind": "database"},
    },
}


def test_universal_compiles_typed_and_dictionary_branches_with_default_mappings():
    from onesite.config import CapabilityBranchConfig, CapabilityKind, UniversalCapabilityConfig

    config = UniversalCapabilityConfig(
        kind=CapabilityKind.UNIVERSAL,
        selector_field="protocol",
        branches={
            name: CapabilityBranchConfig(**branch)
            for name, branch in UNIVERSAL_CONFIG["branches"].items()
        },
    )
    compiled = compile_capabilities(UniversalProfile, [config])
    assert compiled == compile_capabilities(UniversalProfile, [UNIVERSAL_CONFIG])
    by_kind = {entry["kind"]: entry for entry in compiled}
    mqtt = by_kind["mqtt_broker"]
    assert mqtt["selector_field"] == "protocol"
    assert mqtt["selector_values"] == ["mqtt"]
    assert mqtt["fields"] == {"endpoint": "endpoint", "username": "username", "password": "password"}
    assert mqtt["permissions"] == {"subscribe": ["user", "admin"]}
    opcua = by_kind["opcua_server"]
    assert set(opcua["selector_values"]) == {"opcua", "opc_alias"}
    assert opcua["fields"] == {"endpoint": "opcua_url", "username": "username", "password": "opcua_password"}
    database = by_kind["database"]
    assert database["selector_values"] == ["pg"]
    assert database["fields"]["driver"] == "driver"

    explicit = deepcopy(UNIVERSAL_CONFIG)
    explicit["branches"]["postgres"] = {**explicit["branches"].pop("pg"), "when": {"protocol": "pg"}}
    assert compile_capabilities(UniversalProfile, [explicit]) == compiled


@pytest.mark.parametrize(("branch", "override", "error"), [
    ("opc", {"when": {"protocol": ["opcua", "opc_alias", "mqtt"]}}, "overlap"),
    ("opc", {"when": {"protocol": "opcua"}}, "missing branches for enum values"),
    ("opc", {"when": {"protocol": ["opcua", "opc_alias", "unknown"]}}, "must match one or more values"),
    ("opc", {"when": {"username": "opcua"}}, "protocol"),
    ("pg", {"field_map": {"port": "host"}}, "must have type int"),
    ("pg", {"field_map": {"driver": "protocol"}}, "driver"),
    ("pg", {"field_map": {"host": "name"}}, "branch-specific field 'name' needs a default"),
])
def test_universal_rejects_invalid_conditions_and_mappings(branch, override, error):
    config = deepcopy(UNIVERSAL_CONFIG)
    config["branches"][branch].update(override)
    with pytest.raises(ValueError, match=error):
        compile_capabilities(UniversalProfile, [config])


def test_universal_requires_string_enum_selector_and_unique_adapter_kinds():
    config = {**UNIVERSAL_CONFIG, "selector_field": "username"}
    with pytest.raises(ValueError, match="string enum"):
        compile_capabilities(UniversalProfile, [config])
    config = deepcopy(UNIVERSAL_CONFIG)
    config["branches"]["opc"] = {"kind": "mqtt_broker", "when": {"protocol": ["opcua", "opc_alias"]}}
    with pytest.raises(ValueError, match="declared more than once"):
        compile_capabilities(UniversalProfile, [config])


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


def test_universal_generated_app_dispatches_saved_connections(tmp_path, monkeypatch):
    source = tmp_path / "app/models"
    source.mkdir(parents=True)
    (tmp_path / "site_config.py").write_text('from onesite.config import SiteConfig\nconfig = SiteConfig(style="industrial")\n')
    model_source = textwrap.dedent('''
        from enum import Enum
        from onesite.config import OneSiteConfig, UniversalCapabilityConfig
        from sqlmodel import Field, SQLModel

        class Protocol(str, Enum):
            MQTT = "mqtt"
            OPCUA = "opcua"
            OPC_ALIAS = "opc_alias"
            PG = "pg"

        class DatabaseDriver(str, Enum):
            POSTGRESQL = "postgresql"

        class Device(SQLModel, table=True):
            __onesite__ = OneSiteConfig(
                owner_field="owner_id",
                capabilities=[UniversalCapabilityConfig.model_validate(UNIVERSAL_CONFIG)],
            )
            id: int | None = Field(default=None, primary_key=True)
            owner_id: int = Field(foreign_key="user.id")
            name: str
            protocol: Protocol
            endpoint: str | None = None
            username: str | None = None
            password: str | None = None
            opcua_url: str | None = None
            opcua_password: str | None = None
            host: str | None = None
            port: int = 5432
            database: str | None = None
            driver: DatabaseDriver = DatabaseDriver.POSTGRESQL
    ''')
    (source / "devices.py").write_text(model_source.replace("UNIVERSAL_CONFIG", repr(UNIVERSAL_CONFIG)))
    monkeypatch.chdir(tmp_path)
    generate_code()

    generated = tmp_path / "generated"
    frontend = generated / "frontend/src"
    backend = generated / "backend"
    routes = (frontend / "Routes.tsx").read_text()
    assert "/devices/:id/mqtt" in routes
    assert 'selector={ { field: "protocol", values: ["mqtt"] } }' in routes
    detail = (frontend / "pages/device/detail.tsx").read_text()
    assert "<OpcuaCapability" in detail and "<DatabaseCapability" in detail
    assert '"opc_alias"' in detail
    requirements = (backend / "requirements.txt").read_text()
    assert "asyncua" in requirements and "gmqtt" in requirements
    assert "onesite.config" not in (backend / "app/models/devices.py").read_text()

    monkeypatch.setenv("CAPABILITY_SECRET_KEY", "runtime-test-key-only-000000000000000")
    scenario = Path(__file__).resolve().parent / "support/universal_capability_scenario.py"
    result = subprocess.run(
        [sys.executable, "-c", scenario.read_text()], cwd=backend,
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
