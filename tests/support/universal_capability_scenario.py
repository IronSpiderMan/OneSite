"""Verify runtime selection without connecting to external servers."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.endpoints import capability_database, capability_mqtt, capability_opcua
from app.core.db import engine, init_db
from app.core.security import create_access_token
from app.cruds import device as crud
from app.main import app
from app.models.devices import Device, Protocol
from app.models.user import User, UserRole
from app.schemas.device import DeviceUpdate


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def main():
    await init_db()
    async with AsyncSession(engine) as session:
        session.add_all([
            User(id=1, email="owner@example.test", hashed_password="", role=UserRole.USER),
            User(id=2, email="other@example.test", hashed_password="", role=UserRole.USER),
            User(id=3, email="admin@example.test", hashed_password="", role=UserRole.ADMIN),
            User(id=4, email="developer@example.test", hashed_password="", role=UserRole.DEVELOPER),
        ])
        await session.commit()

    calls = []

    async def messages(profile, endpoint, topic_filter):
        calls.append(("mqtt", profile["password"]))
        assert endpoint == ("broker.test", 8883, True)
        assert topic_filter == "devices/#"
        yield 'event: ready\ndata: {}\n\n'

    async def browse(profile, nodeid, **kwargs):
        calls.append(("opcua", profile.password))
        assert profile.endpoint == "opc.tcp://opc.test:4840"
        assert nodeid == "i=84"
        return {"items": []}

    async def execute(statement, parameters):
        assert statement is capability_database._TABLES
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))

    @asynccontextmanager
    async def database(profile):
        calls.append(("database", profile["password"]))
        assert profile == {
            "host": "postgres.test", "port": 5432, "username": "operator",
            "password": "pg-secret", "database": "devices", "driver": "postgresql",
        }
        yield SimpleNamespace(execute=execute)

    capability_mqtt._messages = messages
    capability_opcua.browse = browse
    capability_database._database = database

    collection = "/api/v1/devices/"
    payload = {"name": "Device", "owner_id": 1, "protocol": "mqtt", "username": "operator"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(collection, headers=auth(3), json=payload)
        assert response.status_code == 422, response.text
        response = await client.post(collection, headers=auth(3), json={
            **payload, "endpoint": "mqtts://broker.test", "port": None,
        })
        assert response.status_code == 422, response.text

        response = await client.post(collection, headers=auth(3), json={
            **payload, "endpoint": "mqtts://broker.test", "password": "mqtt-secret",
        })
        assert response.status_code == 200, response.text
        created = response.json()
        assert created["protocol"] == "mqtt" and created["host"] is None and created["opcua_url"] is None
        assert {"password", "opcua_password"}.isdisjoint(created)
        identity = created["id"]
        record_path = f"{collection}{identity}"
        capability_path = f"/api/v1/model-capabilities/device/{identity}"
        mqtt = f"{capability_path}/mqtt_broker/messages"
        opcua = f"{capability_path}/opcua_server/browse"
        tables = f"{capability_path}/database/tables"

        async with AsyncSession(engine) as session:
            record = await session.get(Device, identity)
            assert record.password.startswith("onesite:v1:")
            assert "mqtt-secret" not in record.password and record.opcua_password is None

        response = await client.get(opcua, headers=auth(1))
        assert response.status_code == 404 and not calls, response.text
        response = await client.get(tables, headers=auth(3))
        assert response.status_code == 404 and not calls, response.text
        for user_id, status in [(2, 404), (4, 403), (1, 200)]:
            response = await client.get(mqtt, headers=auth(user_id), params={"topic_filter": "devices/#"})
            assert response.status_code == status, response.text
        assert calls == [("mqtt", "mqtt-secret")]

        response = await client.put(record_path, headers=auth(1), json={"protocol": "opcua"})
        assert response.status_code == 403, response.text
        response = await client.put(record_path, headers=auth(3), json={"opcua_password": "inactive-secret"})
        assert response.status_code == 422 and "inactive-secret" not in response.text, response.text
        response = await client.put(record_path, headers=auth(3), json={"port": None})
        assert response.status_code == 422, response.text

        pg = {"protocol": "pg", "host": "postgres.test", "database": "devices"}
        response = await client.put(record_path, headers=auth(3), json=pg)
        assert response.status_code == 422 and "Re-enter" in response.text, response.text
        response = await client.put(record_path, headers=auth(3), json={**pg, "password": ""})
        assert response.status_code == 422, response.text
        response = await client.get(record_path, headers=auth(3))
        assert response.status_code == 200 and response.json()["protocol"] == "mqtt", response.text

        response = await client.put(record_path, headers=auth(3), json={**pg, "password": "pg-secret"})
        assert response.status_code == 200 and response.json()["protocol"] == "pg", response.text
        response = await client.get(mqtt, headers=auth(1), params={"topic_filter": "devices/#"})
        assert response.status_code == 404, response.text
        response = await client.get(tables, headers=auth(1))
        assert response.status_code == 403, response.text
        response = await client.get(tables, headers=auth(3))
        assert response.status_code == 200 and calls[-1] == ("database", "pg-secret"), response.text
        response = await client.put(record_path, headers=auth(3), json={"host": None, "password": "pg-secret"})
        assert response.status_code == 422, response.text

        response = await client.put(record_path, headers=auth(3), json={"protocol": "opc_alias"})
        assert response.status_code == 422, response.text
        response = await client.put(record_path, headers=auth(3), json={
            "protocol": "opc_alias", "opcua_url": "opc.tcp://opc.test:4840", "opcua_password": "opc-secret",
        })
        assert response.status_code == 200 and response.json()["protocol"] == "opc_alias", response.text
        response = await client.get(tables, headers=auth(3))
        assert response.status_code == 404, response.text
        response = await client.get(opcua, headers=auth(1))
        assert response.status_code == 200 and calls[-1] == ("opcua", "opc-secret"), response.text

        response = await client.put(record_path, headers=auth(3), json={"protocol": "mqtt", "password": ""})
        assert response.status_code == 200, response.text
        response = await client.get(mqtt, headers=auth(1), params={"topic_filter": "devices/#"})
        assert response.status_code == 200 and calls[-1] == ("mqtt", ""), response.text
        response = await client.put(record_path, headers=auth(3), json={"protocol": "opcua"})
        assert response.status_code == 422 and "Re-enter" in response.text, response.text

    assert calls == [("mqtt", "mqtt-secret"), ("database", "pg-secret"), ("opcua", "opc-secret"), ("mqtt", "")]

    async with AsyncSession(engine) as stale, AsyncSession(engine) as concurrent:
        stale_record = await stale.get(Device, identity)
        current_record = await concurrent.get(Device, identity)
        await crud.update(concurrent, current_record, DeviceUpdate(protocol=Protocol.OPCUA, opcua_password=""))
        try:
            await crud.update(stale, stale_record, DeviceUpdate(endpoint="mqtts://other.test"))
        except HTTPException as error:
            assert error.status_code == 409
        else:
            raise AssertionError("Expected a conflict for a stale profile update")

    async with AsyncSession(engine) as session:
        record = await session.get(Device, identity)
        assert record.protocol == Protocol.OPCUA and record.endpoint == "mqtts://broker.test"


asyncio.run(main())
