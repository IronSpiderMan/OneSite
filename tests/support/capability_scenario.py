"""Exercise a generated app without contacting external services."""

import asyncio
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.endpoints import capability_database, capability_opcua
from app.core.db import engine, init_db
from app.core.security import create_access_token
from app.main import app
from app.models.connections import Gateway
from app.models.user import User, UserRole


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def main():
    await init_db()
    async with AsyncSession(engine) as session:
        session.add_all([
            User(id=1, email="owner@example.test", hashed_password="", role=UserRole.USER),
            User(id=2, email="other@example.test", hashed_password="", role=UserRole.USER),
            User(id=3, email="admin@example.test", hashed_password="", role=UserRole.ADMIN),
            User(id=4, email="dev@example.test", hashed_password="", role=UserRole.DEVELOPER),
        ])
        await session.commit()

    async def browse(profile, nodeid, **kwargs):
        assert profile.endpoint == "opc.tcp://plant.test:4840"
        assert profile.password == "the-secret"
        assert nodeid == "i=84"
        return {"items": []}

    capability_opcua.browse = browse

    @asynccontextmanager
    async def database(profile):
        assert profile == {"host": "warehouse.test", "port": 5432, "username": "readonly",
                           "password": "pw", "database": "warehouse", "driver": "postgresql"}
        yield object()

    async def rows(connection, query):
        assert query.schema_name == "public" and query.table == "events"
        return {"columns": ["id"], "rows": [["1"]], "page": 1, "page_size": 25,
                "has_more": False, "truncated": False}

    capability_database._database = database
    capability_database._read_rows = rows
    payload = {"id": "west-1", "owner_id": 1, "name": "West gateway",
               "address": "opc.tcp://plant.test:4840", "broker_url": "mqtts://plant.test",
               "username": "operator", "credential": "the-secret"}
    model_path = "/api/v1/gateways/west-1"
    capability_path = "/api/v1/model-capabilities/gateway/west-1"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/v1/gateways/", headers=auth(3), json=payload)
        assert created.status_code == 200, created.text
        for path in (model_path, "/api/v1/gateways/"):
            response = await client.get(path, headers=auth(3))
            assert response.status_code == 200 and "credential" not in response.text, response.text
        async with AsyncSession(engine) as session:
            record = await session.get(Gateway, "west-1")
            assert record.credential.startswith("onesite:v1:")
            assert "the-secret" not in record.credential

        for user_id, expected in [(1, 200), (2, 404), (3, 200), (4, 403)]:
            response = await client.get(f"{capability_path}/opcua_server/browse", headers=auth(user_id))
            assert response.status_code == expected, response.text
        response = await client.get(f"{capability_path}/mqtt_broker/messages?topic_filter=telemetry", headers=auth(1))
        assert response.status_code == 403, response.text
        response = await client.put(model_path, headers=auth(1), json={"address": "opc.tcp://other.test"})
        assert response.status_code == 403, response.text
        response = await client.put(model_path, headers=auth(3), json={"address": "opc.tcp://other.test"})
        assert response.status_code == 422 and "Re-enter" in response.text, response.text
        response = await client.put(model_path, headers=auth(3), json={"name": "Renamed"})
        assert response.status_code == 200 and "credential" not in response.text, response.text
        response = await client.put(model_path, headers=auth(3), json={"credential": ["invalid-secret"]})
        assert response.status_code == 422 and "invalid-secret" not in response.text, response.text
        response = await client.put(model_path, headers=auth(3), json={"address": "opc.tcp://other.test", "credential": ""})
        assert response.status_code == 200 and "credential" not in response.text, response.text
        response = await client.post("/api/v1/warehouses/", headers=auth(3), json={
            "host": "warehouse.test", "username": "readonly", "password": "pw", "database": "warehouse",
        })
        assert response.status_code == 200 and "password" not in response.text, response.text
        database_path = f"/api/v1/model-capabilities/warehouse/{response.json()['id']}/database"
        query = {"schema": "public", "table": "events"}
        response = await client.post(f"{database_path}/query", headers=auth(1), json=query)
        assert response.status_code == 403, response.text
        response = await client.post(f"{database_path}/query", headers=auth(3), json=query)
        assert response.status_code == 200 and response.json()["rows"] == [["1"]], response.text
        response = await client.post(f"{database_path}/query", headers=auth(3), json={**query, "sql": "SELECT 1"})
        assert response.status_code == 422, response.text


asyncio.run(main())
