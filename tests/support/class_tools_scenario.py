"""Exercise real class tools in a standalone generated backend."""

import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.core.background_execution import BackgroundExecution
from app.core.config import settings
from app.core.db import engine, init_db
from app.core.security import create_access_token
from app.core.task_queue import task_queue
from app.handlers.tool_execution import execute_tool
from app.models.user import User, UserRole


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def main():
    await init_db()
    async with AsyncSession(engine) as session:
        session.add_all(
            [
                User(id=1, email="admin@example.test", hashed_password="", role=UserRole.ADMIN),
                User(id=2, email="user@example.test", hashed_password="", role=UserRole.USER),
            ]
        )
        await session.commit()
    pending = []
    task_queue.publish = lambda topic, payload: pending.append(payload)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        endpoint = "/api/v1/tools/transform/execute"
        assert (await client.post(endpoint, json={"text": "hello"})).status_code == 401
        assert (
            await client.post(endpoint, headers=auth(2), json={"text": "hello"})
        ).status_code == 403
        for invalid in (
            {},
            {"text": ""},
            {"text": "bad"},
            {"text": "ok", "count": 3},
            {"text": "ok", "count": "0"},
            {"text": "ok", "unknown": 1},
        ):
            response = await client.post(endpoint, headers=auth(1), json=invalid)
            assert response.status_code == 422, response.text
            assert not pending
        for _ in range(2):
            response = await client.post(
                endpoint,
                headers=auth(1),
                json={
                    "text": "Hello",
                    "count": 0,
                    "flag": False,
                    "optional": None,
                    "mode": 1,
                    "rows": [{"name": "nested"}],
                },
            )
            assert response.status_code == 202, response.text
            task_id = response.json()["task_id"]
            token = pending[-1]["inputs"]["token"]
            await execute_tool(pending.pop())
            execution = await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(1))
            data = execution.json()
            assert data["status"] == "succeeded", data
            result = data["result"]
            assert result["content"] == "hello", result
            assert result["count"] == 0 and result["flag"] is False and result["optional"] is None
            assert result["token"] == token
            assert result["day"] == "2026-10-30" and result["invocations"] == 1
            assert result["rows"] == [{"name": "nested"}]
            assert (
                await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(2))
            ).status_code == 404
        response = await client.post(
            endpoint, headers=auth(1), data={"__inputs__": json.dumps({"text": "multipart"})}
        )
        assert response.status_code == 202, response.text
        await execute_tool(pending.pop())

        response = await client.post(
            "/api/v1/tools/bad_result/execute", headers=auth(1), json={"text": "valid"}
        )
        task_id = response.json()["task_id"]
        await execute_tool(pending.pop())
        data = (await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(1))).json()
        assert data["status"] == "failed" and "validation" in data["error"], data

        response = await client.post(
            "/api/v1/tools/aliased/execute", headers=auth(1), json={"incoming": "secret"}
        )
        assert response.status_code == 202, response.text
        task_id = response.json()["task_id"]
        assert pending[-1]["inputs"] == {"incoming": "secret"}
        async with AsyncSession(engine) as session:
            execution = await session.get(BackgroundExecution, task_id)
            assert json.loads(execution.inputs_json) == {}
        await execute_tool(pending.pop())
        data = (await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(1))).json()
        assert data["status"] == "succeeded", data
        assert data["result"] == {"rendered": "secret", "length": 6}, data

        files_endpoint = "/api/v1/tools/merge_files/execute"
        response = await client.post(
            files_endpoint,
            headers=auth(1),
            json={"upload": {"path": "/etc/passwd", "name": "fake", "size": 0}},
        )
        assert response.status_code == 422, response.text
        for filename, content, expected in (
            ("bad.csv", b"bad", 422),
            ("large.txt", b"x" * 2000, 413),
        ):
            response = await client.post(
                files_endpoint, headers=auth(1), files={"upload": (filename, content)}
            )
            assert response.status_code == expected, response.text
        response = await client.post(
            files_endpoint,
            headers=auth(1),
            files=[("upload", ("first.txt", b"first")), ("others", ("second.txt", b"second"))],
        )
        assert response.status_code == 202, response.text
        task_id = response.json()["task_id"]
        async with AsyncSession(engine) as session:
            execution = await session.get(BackgroundExecution, task_id)
            assert "path" not in json.loads(execution.inputs_json)["upload"]
        await execute_tool(pending.pop())
        data = (await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(1))).json()
        assert data["status"] == "succeeded", data
        report = data["result"]["report"]
        assert report["size"] == 11 and "path" not in report, report
        response = await client.get(report["download_url"])
        assert response.status_code == 200 and response.content == b"firstsecond", response.text
        # Failed uploads have no leaked files. Only the successful upload remains.
        assert len(list((Path(settings.UPLOAD_DIR) / "tools").glob("*/inputs/*/*"))) == 2

        response = await client.post(endpoint, headers=auth(1), json={"text": "queued"})
        task_id = response.json()["task_id"]
        async with AsyncSession(engine) as session:
            user = await session.get(User, 1)
            user.role = UserRole.USER
            session.add(user)
            await session.commit()
        await execute_tool(pending.pop())
        data = (await client.get(f"/api/v1/tools/executions/{task_id}", headers=auth(1))).json()
        assert data["status"] == "failed" and data["error"] == "Permission denied", data
    await engine.dispose()
    assert not any(
        name == "onesite" or name.startswith("onesite.") or name == "onesite_runtime"
        for name in sys.modules
    )


asyncio.run(main())
