"""OPC UA plugin generation, profile validation and live address-space browsing."""

import importlib
import socket
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from onesite.codegen.model_imports import isolated_project_imports
from onesite.codegen.phases.plugin_models import phase_generate_plugin_models
from onesite.codegen.phases.sync_models import phase_sync_models
from onesite_runtime import ReadContext, resolve_read_data


def generate(tmp_path):
    # A fresh process keeps SQLAlchemy's global mapper registry independent of
    # generator introspection and unrelated test model classes.
    backend = tmp_path / "generated/backend"
    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models({"plugins": ["opcua"]}, tmp_path, backend)
    from onesite.codegen.render import generate_file

    model = {
        "name": "OpcuaServer",
        "source_module": "opcua_server",
        "module_name": "opcua_server",
        "role_permissions": {"user": "", "admin": "r", "developer": "crud"},
    }
    generate_file("opcua_runtime.py.j2", {}, backend / "app/core/opcua.py")
    generate_file(
        "opcua_browse_api.py.j2", {"model": model}, backend / "app/api/endpoints/opcua_browse.py"
    )
    (backend / "app/core/config.py").write_text(
        f"from types import SimpleNamespace\nsettings = SimpleNamespace(UPLOAD_DIR={str(tmp_path / 'uploads')!r}, PRIVATE_UPLOAD_DIR={str(tmp_path / 'private')!r})\n"
    )
    return backend, {}


def load_models():
    server = importlib.import_module("app.models.opcua_server").OpcuaServer
    node = importlib.import_module("app.models.opcua_node").OpcuaNode
    ac = importlib.import_module("app.models.opcua_ac").OpcuaAc
    return server, node, ac


async def test_profile_validation_and_secrets(tmp_path):
    backend, _ = generate(tmp_path)
    with isolated_project_imports(backend):
        Server, Node, Ac = load_models()
        server = Server(
            title="PLC",
            endpoint="opc.tcp://localhost:4840",
            auth_type="username",
            username="operator",
            password="secret",
        )
        await server.on_before_create()
        changes = {"password": "", "title": "new"}
        await server.on_before_update(changes)
        assert "password" not in changes
        assert (
            await resolve_read_data(
                server, {"password": "secret"}, ReadContext(session=None, source="detail")
            )
        )["password"] == ""
        for changes in (
            {"endpoint": "http://localhost"},
            {"endpoint": "opc.tcp://user:secret@localhost"},
            {"username": ""},
            {"request_timeout_seconds": 0},
            {"request_timeout_seconds": float("nan")},
            {"security_policy": "unknown"},
            {"security_policy": "Basic256Sha256", "security_mode": "Sign"},
        ):
            with pytest.raises(ValueError):
                await server.on_before_update(changes)
        for value in (
            "i=0",
            "ns=0;i=0",
            "ns=65536;i=1",
            "i=-1",
            "i=4294967296",
            "not-a-node",
            "g=invalid",
            "b=invalid",
        ):
            with pytest.raises(ValueError):
                Node(title="point", opcua_server_id=1, nodeid=value).on_before_create()
        for value in (
            "i=2253",
            "ns=2;s=A",
            "nsu=urn:example;v=1;s=A",
            "g=8128efc4-e9c1-4e1d-b390-ab2ea8048135",
            "b=YWJj",
        ):
            Node(title="point", opcua_server_id=1, nodeid=value).on_before_create()
        with pytest.raises(ValueError):
            Node(
                title="point", opcua_server_id=1, nodeid="i=1", collection_mode="bad"
            ).on_before_create()
        with pytest.raises(HTTPException) as error:
            Ac(title="alarm", opcua_server_id=1, condition_id="bad").on_before_create()
        assert error.value.status_code == 422
        Ac(
            title="alarm", opcua_server_id=1, condition_id="nsu=urn:example;s=Alarm"
        ).on_before_create()
        runtime = importlib.import_module("app.core.opcua")
        assert runtime.certificate_path("/private-uploads/key.pem") == str(
            tmp_path / "private/key.pem"
        )
        for path in ("/uploads/../key.pem", "/private-uploads/..", "https://example.com/key"):
            with pytest.raises(ValueError):
                runtime.certificate_path(path)


async def test_database_uniqueness_and_cascade(tmp_path):
    backend, _ = generate(tmp_path)
    with isolated_project_imports(backend):
        Server, Node, Ac = load_models()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda conn: SQLModel.metadata.create_all(
                    conn, tables=[m.__table__ for m in (Server, Node, Ac)]
                )
            )
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                first = Server(title="A", endpoint="opc.tcp://localhost:4840")
                second = Server(title="B", endpoint=first.endpoint)
                session.add_all([first, second])
                await session.commit()
                await session.refresh(first)
                assert type(first.auth_type).__name__ == "OpcuaAuthType"
                assert type(first.security_policy).__name__ == "OpcuaSecurityPolicy"
                assert type(first.security_mode).__name__ == "OpcuaSecurityMode"
                session.add_all(
                    [
                        Node(title="Temperature", opcua_server_id=s.id, nodeid="ns=2;s=Temperature")
                        for s in (first, second)
                    ]
                )
                session.add(Ac(title="High", opcua_server_id=first.id, condition_id="ns=2;s=High"))
                await session.commit()
                first_id = first.id
                duplicate = Node(
                    title="Other", opcua_server_id=first.id, nodeid="ns=2;s=Temperature"
                )
                session.add(duplicate)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
                first = await session.get(Server, first_id)
                await session.delete(first)
                await session.commit()
                from sqlmodel import select

                assert len((await session.exec(select(Node))).all()) == 1
                assert not (await session.exec(select(Ac))).all()
        finally:
            await engine.dispose()


async def test_live_browse_with_custom_condition_and_namespace_uri(tmp_path):
    import asyncua

    backend, _ = generate(tmp_path)
    with isolated_project_imports(backend):
        Server, _, _ = load_models()
        runtime = importlib.import_module("app.core.opcua")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = asyncua.Server()
        await server.init()
        server.set_endpoint(f"opc.tcp://127.0.0.1:{port}/test/")
        ns = await server.register_namespace("urn:onesite:test;v=1")
        device = await server.nodes.objects.add_object(ns, "Device")
        variable = await device.add_variable(ns, "Temperature", 25.0)
        subtype = await server.get_node(asyncua.ua.ObjectIds.ConditionType).add_object_type(
            ns, "CustomCondition"
        )
        condition = await device.add_object(ns, "High", subtype.nodeid)
        profile = Server(title="test", endpoint=f"opc.tcp://127.0.0.1:{port}/test/")
        async with server:
            root = await runtime.browse(profile, "i=84")
            assert any(row["nodeid"] == "i=85" for row in root["items"])
            result = await runtime.browse(profile, device.nodeid.to_string())
            rows = {row["nodeid"]: row for row in result["items"]}
            assert rows[variable.nodeid.to_string()]["node_class"] == "Variable"
            assert rows[condition.nodeid.to_string()]["is_condition"]
            assert rows[condition.nodeid.to_string()]["stable_nodeid"].startswith(
                "nsu=urn:onesite:test;v=1;"
            )
            stable_device = f"nsu=urn:onesite:test;v=1;i={device.nodeid.Identifier}"
            assert (await runtime.browse(profile, stable_device))["items"] == result["items"]


def test_browse_api_permissions_validation_and_error_redaction(tmp_path, monkeypatch):
    backend, _ = generate(tmp_path)
    with isolated_project_imports(backend):
        Server, _, _ = load_models()
        actor = SimpleNamespace(allowed=False)
        record = Server(title="PLC", endpoint="opc.tcp://localhost:4840")
        session = SimpleNamespace(get=AsyncMock(return_value=record))

        async def get_session():
            yield session

        def model_access(permissions):
            async def check():
                if not actor.allowed:
                    raise HTTPException(403)

            return check

        for name, attrs in {
            "app.core.db": {"get_session": get_session},
            "app.core.deps": {"model_access": model_access},
            "app.core.access": {"require_owned_record": AsyncMock()},
        }.items():
            module = types.ModuleType(name)
            module.__dict__.update(attrs)
            monkeypatch.setitem(sys.modules, name, module)
        api = importlib.import_module("app.api.endpoints.opcua_browse")
        app = FastAPI()
        app.include_router(api.router, prefix="/opcua")
        with (
            TestClient(app) as client,
            patch.object(api, "browse", new_callable=AsyncMock) as browse,
        ):
            url = "/opcua/1/browse"
            assert client.get(url).status_code == 403
            browse.assert_not_called()
            actor.allowed = True
            assert client.get(url, params={"nodeid": "bad"}).status_code == 422
            browse.assert_not_called()
            browse.return_value = {"items": []}
            assert client.get(url).json() == {"items": []}
            browse.side_effect = RuntimeError("password=SECRET /private/key.pem")
            response = client.get(url)
            assert response.status_code == 502
            assert "SECRET" not in response.text and "key.pem" not in response.text
            session.get.return_value = None
            assert client.get(url).status_code == 404


async def test_live_secure_browse_uses_saved_certificates(tmp_path):
    import asyncua
    from asyncua.crypto.cert_gen import setup_self_signed_certificate
    from cryptography.x509.oid import ExtendedKeyUsageOID

    backend, _ = generate(tmp_path)
    with isolated_project_imports(backend):
        Server, _, _ = load_models()
        runtime = importlib.import_module("app.core.opcua")
        server_key, server_cert = tmp_path / "server-key.pem", tmp_path / "server.der"
        client_key, client_cert = tmp_path / "client-key.pem", tmp_path / "client.der"
        await setup_self_signed_certificate(
            server_key,
            server_cert,
            "urn:onesite:server",
            "localhost",
            [ExtendedKeyUsageOID.SERVER_AUTH],
            {},
        )
        await setup_self_signed_certificate(
            client_key,
            client_cert,
            "urn:onesite:client",
            "localhost",
            [ExtendedKeyUsageOID.CLIENT_AUTH],
            {},
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = asyncua.Server()
        await server.init()
        await server.set_application_uri("urn:onesite:server")
        server.set_endpoint(f"opc.tcp://127.0.0.1:{port}/test/")
        await server.load_certificate(server_cert)
        await server.load_private_key(server_key)
        server.set_security_policy([asyncua.ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt])
        profile = Server(
            title="secure",
            endpoint=f"opc.tcp://127.0.0.1:{port}/test/",
            security_policy="Basic256Sha256",
            security_mode="SignAndEncrypt",
            cert_path=str(client_cert),
            key_path=str(client_key),
            server_cert_path=str(server_cert),
        )
        await profile.on_before_create()
        async with server:
            result = await runtime.browse(profile, "i=84")
            assert any(row["nodeid"] == "i=85" for row in result["items"])


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    scenario, directory = sys.argv[1:]
    function = globals()["test_" + scenario]
    if scenario == "browse_api_permissions_validation_and_error_redaction":
        with pytest.MonkeyPatch.context() as monkeypatch:
            function(Path(directory), monkeypatch)
    else:
        asyncio.run(function(Path(directory)))
