"""Test the generated AlarmHub example against a real, temporary OPC UA server."""

import asyncio
import os
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from mock_opcua import NAMESPACE, make_server

PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "generated/backend"


def check_http():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.config import settings

    def expect(response, status=200):
        assert response.status_code == status, response.text
        return response.json()

    with TestClient(app) as client:

        def login(email, password):
            token = expect(
                client.post(
                    "/api/v1/login/access-token",
                    data={
                        "username": email,
                        "password": password,
                    },
                )
            )["access_token"]
            return {"Authorization": f"Bearer {token}"}

        headers = login(settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD)
        servers = expect(client.get("/api/v1/opcua_servers/", headers=headers))["items"]
        assert len(servers) == 1
        sid = servers[0]["id"]
        url = f"/api/v1/opcua/{sid}/browse"
        expect(client.get(url), 401)
        root = expect(client.get(url, headers=headers))["items"]
        assert any(row["nodeid"] == "i=85" for row in root)
        items = expect(
            client.get(
                url,
                headers=headers,
                params={
                    "nodeid": f"nsu={NAMESPACE};s=Boiler01",
                },
            )
        )["items"]
        entries = {row["title"]: row for row in items}
        assert set(entries) == {
            "Temperature",
            "Pressure",
            "Running",
            "HighTemperature",
            "HighPressure",
        }
        assert entries["Temperature"]["node_class"] == "Variable"
        assert entries["HighPressure"]["is_condition"] is True
        assert entries["HighTemperature"]["is_condition"] is True
        pressure = {
            "title": "压力（Browse 添加）",
            "opcua_server_id": sid,
            "nodeid": entries["Pressure"]["stable_nodeid"],
        }
        node = expect(client.post("/api/v1/opcua_nodes/", headers=headers, json=pressure))
        expect(client.post("/api/v1/opcua_nodes/", headers=headers, json=pressure), 409)
        ac = expect(
            client.post(
                "/api/v1/opcua_acs/",
                headers=headers,
                json={
                    "title": "高压（Browse 添加）",
                    "opcua_server_id": sid,
                    "condition_id": entries["HighPressure"]["stable_nodeid"],
                },
            )
        )
        assert ac["event_notifier_nodeid"] == "i=2253"
        categories = expect(client.get("/api/v1/categorys/", headers=headers))["items"]
        category_id = categories[0]["id"]
        for source, field, identity in (
            ("value", "opcua_node_id", node["id"]),
            ("ac", "opcua_ac_id", ac["id"]),
        ):
            rule = expect(
                client.post(
                    "/api/v1/rules/",
                    headers=headers,
                    json={
                        "title": f"新增 {source} 规则",
                        "category_id": category_id,
                        "source_type": source,
                        field: identity,
                    },
                )
            )
            assert rule[field] == identity
            assert rule[field + "_label"]
        expect(
            client.post(
                "/api/v1/rules/",
                headers=headers,
                json={
                    "title": "缺少条件的错误规则",
                    "category_id": category_id,
                    "source_type": "ac",
                },
            ),
            400,
        )
        for role in ("admin", "user"):
            email = f"{role}@alarmhub.example"
            expect(
                client.post(
                    "/api/v1/users/",
                    headers=headers,
                    json={
                        "email": email,
                        "password": "demo-test-password",
                        "role": role,
                    },
                )
            )
            role_headers = login(email, "demo-test-password")
            expect(client.get(url, headers=role_headers), 200 if role == "admin" else 403)
            expect(client.post("/api/v1/opcua_nodes/", headers=role_headers, json=pressure), 403)
        expect(client.get(url, headers=headers, params={"nodeid": "invalid"}), 422)
        expect(
            client.put(
                f"/api/v1/opcua_servers/{sid}",
                headers=headers,
                json={"endpoint": "opc.tcp://127.0.0.1:1/", "request_timeout_seconds": 1},
            )
        )
        failure = expect(client.get(url, headers=headers), 502)
        assert "127.0.0.1:1" not in str(failure)
    print(
        "PASS: real Browse (5 nodes), point/A&C creation, duplicate checks, business FKs, roles and errors."
    )


async def main():
    if not (BACKEND / "app/main.py").exists():
        raise SystemExit("Run site sync in examples/alarmhub first.")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    endpoint = f"opc.tcp://127.0.0.1:{port}/alarmhub/"
    with TemporaryDirectory(prefix="alarmhub-smoke-") as temp:
        os.environ["DATABASE_URI"] = f"sqlite:///{temp}/test.db"
        os.environ["ALARMHUB_OPCUA_ENDPOINT"] = endpoint
        os.chdir(BACKEND)
        sys.path.insert(0, str(BACKEND))
        server, _ = await make_server(endpoint)
        async with server:
            await asyncio.to_thread(check_http)


if __name__ == "__main__":
    asyncio.run(main())
