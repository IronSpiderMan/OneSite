"""Full task lifecycle using generated standalone code and APScheduler."""

import asyncio
import json
import sys

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.core.background_execution import BackgroundExecution
from app.core.db import engine, init_db
from app.core.scheduler import TaskRegistry, task_registry
from app.core.scheduled_task_bindings import register_scheduled_tasks, SCHEDULED_TASK_DEFINITIONS
from app.core.scheduled_task_runtime import recover_scheduled_executions
from app.core.security import create_access_token
from app.core.task_queue import task_queue
from app.handlers.scheduled_task_execution import execute_scheduled_task
from app.models.user import User, UserRole


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def main():
    await init_db()
    # Exercise the additive migration of an existing unversioned runtime table.
    async with engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE onesite_background_execution DROP COLUMN payload_json")
        )
    await init_db()
    async with engine.begin() as connection:
        columns = await connection.run_sync(
            lambda conn: inspect(conn).get_columns("onesite_background_execution")
        )
        assert "payload_json" in {column["name"] for column in columns}
    async with AsyncSession(engine) as session:
        session.add_all(
            [
                User(id=1, email="admin@example.test", hashed_password="", role=UserRole.ADMIN),
                User(id=2, email="user@example.test", hashed_password="", role=UserRole.USER),
            ]
        )
        await session.commit()

    pending = []
    tick = asyncio.Event()

    def publish(topic, payload):
        pending.append(payload)
        tick.set()

    task_queue.publish = publish
    register_scheduled_tasks()
    task_registry.start()
    task_registry._scheduler.pause()
    assert isinstance(task_registry._scheduler.get_job("report").trigger, IntervalTrigger)
    missing = task_registry.get_task("missing_params")
    assert missing["enabled"] is False and missing["configuration_error"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        async def execution(execution_id):
            response = await client.get(f"/api/v1/tasks/executions/{execution_id}", headers=auth(1))
            assert response.status_code == 200, response.text
            return response.json()

        assert (await client.get("/api/v1/tasks/")).status_code == 401
        assert (await client.get("/api/v1/tasks/", headers=auth(2))).json() == []
        assert (await client.post("/api/v1/tasks/report/run", headers=auth(2))).status_code == 403
        listed = (await client.get("/api/v1/tasks/", headers=auth(1))).json()
        assert any(item.get("inputs") for item in listed)
        assert (
            await client.post("/api/v1/tasks/needs_params/enable", headers=auth(1))
        ).status_code == 422
        before = task_registry.get_task("report")
        response = await client.put(
            "/api/v1/tasks/report",
            headers=auth(1),
            json={"cron": "*/5 * * * *", "params": {"limit": -1}},
        )
        assert response.status_code == 422, response.text
        assert task_registry.get_task("report")["interval"] == before["interval"]
        assert task_registry.get_task("report")["input_overrides"] == {}
        for invalid in ({"limit": "0"}, {"unknown": 1}, {"limit": 2, "rows": [{"name": "one"}]}):
            response = await client.put(
                "/api/v1/tasks/report", headers=auth(1), json={"params": invalid}
            )
            assert response.status_code == 422, response.text
        response = await client.put(
            "/api/v1/tasks/report",
            headers=auth(1),
            json={"params": {"limit": 0, "flag": False, "optional": None, "credential": "private"}},
        )
        assert response.status_code == 200, response.text
        state = json.loads(task_registry._state_file.read_text())["report"]
        assert state["input_overrides"] == {
            "limit": 0,
            "flag": False,
            "optional": None,
            "credential": "private",
        }
        assert (
            "params" not in state
            and "token" not in state["input_overrides"]
            and "inputs" not in state
        )

        tokens = []
        for _ in range(2):
            response = await client.post("/api/v1/tasks/report/run", headers=auth(1))
            assert response.status_code == 202, response.text
            task_id = response.json()["execution_id"]
            payload = pending.pop()
            tokens.append(payload["params"]["token"])
            async with AsyncSession(engine) as session:
                record = await session.get(BackgroundExecution, task_id)
                assert "credential" not in json.loads(record.inputs_json)
                assert "payload_json" not in record.model_dump()
                assert json.loads(record.payload_json)["credential"] == "private"
            await execute_scheduled_task(payload)
            record = await execution(task_id)
            assert record["status"] == "succeeded", record
            output = record["result"]
            assert output["count"] == 0 and output["flag"] is False and output["optional"] is None
            assert output["token"] == tokens[-1] and output["day"] == "2026-10-30"
            assert (
                output["user_id"] == 1
                and output["trigger"] == "manual"
                and output["invocations"] == 1
            )
            assert output["report"]["download_url"].startswith("/uploads/scheduled_tasks/")
            assert (await client.get(record["download_url"])).text == "0"
        assert tokens[0] != tokens[1]

        # Restart recovery preserves excluded inputs and factory values exactly.
        response = await client.post("/api/v1/tasks/report/run", headers=auth(1))
        task_id = response.json()["execution_id"]
        snapshot = pending.pop()["params"]
        await recover_scheduled_executions()
        assert pending[-1]["params"] == snapshot
        await execute_scheduled_task(pending.pop())
        assert (await execution(task_id))["result"]["token"] == snapshot["token"]

        # Concurrent skip checks cover actual queued work, not just APScheduler callbacks.
        records = await asyncio.gather(
            task_registry.run("report", 1), task_registry.run("report", 1)
        )
        assert records[0].id == records[1].id and len(pending) == 1
        await execute_scheduled_task(pending.pop())
        records = await asyncio.gather(
            task_registry.run("queued", 1), task_registry.run("queued", 1)
        )
        assert records[0].id != records[1].id and len(pending) == 2
        while pending:
            await execute_scheduled_task(pending.pop(0))
        record = await task_registry.run("bad_result", 1)
        await execute_scheduled_task(pending.pop())
        assert (await execution(record.id))["status"] == "failed"
        record = await task_registry.run("legacy", 1)
        await execute_scheduled_task(pending.pop())
        assert (await execution(record.id))["result"] == {"region": "cn"}

        response = await client.put(
            "/api/v1/tasks/report",
            headers=auth(1),
            json={"params": {}, "cron": "*/5 * * * *", "interval": 0},
        )
        assert response.status_code == 200, response.text
        assert isinstance(task_registry._scheduler.get_job("report").trigger, CronTrigger)
        assert str(task_registry._scheduler.get_job("report").trigger.fields[6]) == "*/5"
        new_registry = TaskRegistry()
        for definition in SCHEDULED_TASK_DEFINITIONS:
            new_registry.register({**definition, "func": definition.get("class_path", "legacy")})
        new_registry.load_state()
        assert new_registry.get_task("report")["input_overrides"] == {}
        assert "token" not in new_registry._input_values(new_registry._tasks["report"])

        # Use the actual APScheduler callback, with no user identity.
        await task_registry._scheduler.get_job("report").func()
        task_id = pending[-1]["execution_id"]
        await execute_scheduled_task(pending.pop())
        output = (await execution(task_id))["result"]
        assert (
            output["trigger"] == "schedule" and output["user_id"] is None and output["count"] == 3
        )

        # Recheck permissions at consumption, without assigning roles to automatic work.
        record = await task_registry.run("report", 1)
        async with AsyncSession(engine) as session:
            user = await session.get(User, 1)
            user.role = UserRole.USER
            session.add(user)
            await session.commit()
        await execute_scheduled_task(pending.pop())
        async with AsyncSession(engine) as session:
            record = await session.get(BackgroundExecution, record.id)
            assert record.status == "failed" and record.error == "Permission denied"

        # Finally let the real clock trigger an APScheduler interval job.
        task_registry.update("report", {"interval": 1})
        tick.clear()
        task_registry._scheduler.resume()
        await asyncio.wait_for(tick.wait(), timeout=4)
        task_registry._scheduler.pause()
        assert any(payload["task_name"] == "report" for payload in pending)
    task_registry.stop()
    await engine.dispose()
    assert not any(
        name == "onesite" or name.startswith("onesite.") or name == "onesite_runtime"
        for name in sys.modules
    )


asyncio.run(main())
