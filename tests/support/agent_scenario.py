# ruff: noqa: E402
# Imports of generated app modules must follow code generation and sys.path setup.
"""Exercise generated APIs in an isolated interpreter and SQLite database."""

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner
from onesite.main import app as cli

root = Path(sys.argv[1])
os.chdir(root)
runner = CliRunner()
created = runner.invoke(cli, ["create", "AgentIntegration"])
assert created.exit_code == 0, created.output
project = root / "AgentIntegration"
(project / "site_config.py").write_text(
    'import os\nfrom onesite.config import SiteConfig\nconfig = SiteConfig(database_url=os.environ.get("ONESITE_AGENT_TEST_DATABASE_URL", "sqlite:///./app.db"), agents={"assistant":{"model":"test","roles":["user","admin","developer"],"model_tools":{"Note":["crud","bulk_delete","import"]},"custom_tools":["echo"]}})\n'
)
(project / "app/models/note.py").write_text("""from sqlmodel import SQLModel, Field
class Note(SQLModel, table=True):
    __onesite__ = {"importable": True, "permissions": {"user":"r", "admin":"crud", "developer":"crud"}}
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(unique=True)
    owner_id: int | None = Field(default=None, foreign_key="user.id")
    secret: str = Field(default="hidden", sa_column_kwargs={"info":{"site_props":{"permissions":{"user":"","admin":"cru","developer":"cru"}}}})
""")
(project / "app/agent_tools").mkdir()
(project / "app/agent_tools/echo.py").write_text(
    'from pydantic import BaseModel\nfrom typing import Literal\nfrom datetime import date\nfrom app.core.agent_tools import agent_tool\nclass Args(BaseModel):\n    text: str\n    enabled: bool = False\n    count: int = 1\n    tag: Literal["a", "b"] = "a"\n    when: date | None = None\n    meta: dict | None = None\n@agent_tool(args_model=Args, roles=["admin"])\nasync def echo(args, context):\n    return {"text": args.text}\n'
)
os.chdir(project)
synced = runner.invoke(cli, ["sync"])
assert synced.exit_code == 0, synced.output
sys.path.insert(0, str(project / "generated/backend"))
os.chdir(project / "generated/backend")
os.environ["AGENT_API_KEY"] = "test-only"

import httpx
from jose import jwt
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.main import app
from app.core import db
from app.core.config import settings
from app.core.agent import AgentContext, AgentBlocked, ToolArgumentsOverride
from app.core.agent_models import AgentSession, AgentMessage, now
from datetime import timedelta
from app.core.agent_tools import ToolRegistry, AGENTS
from app.api.endpoints import agents
from app.models.user import User, UserRole


def token(user):
    return "Bearer " + jwt.encode({"sub": str(user.id)}, settings.SECRET_KEY, algorithm="HS256")


async def main():
    await db.init_db()
    async with AsyncSession(db.engine, expire_on_commit=False) as session:
        admin = User(email="admin@test", hashed_password="not-a-password", role=UserRole.ADMIN)
        user = User(email="user@test", hashed_password="not-a-password", role=UserRole.USER)
        session.add(admin)
        session.add(user)
        await session.commit()
    admin_auth = {"Authorization": token(admin)}
    user_auth = {"Authorization": token(user)}
    registry = ToolRegistry(app, AGENTS["assistant"], AgentContext(admin, "s", "r"), token(admin))
    assert await registry.execute("echo", {"text": "custom"}) == {"text": "custom"}
    # Real generated endpoints, parameter schemas and business persistence.
    created = await registry.execute(
        "Note_create", {"body": {"title": "hello", "secret": "private"}}
    )
    assert created["title"] == "hello", created
    note_id = created["id"]
    updated = await registry.execute("Note_update", {"id": note_id, "body": {"title": "updated"}})
    assert updated["title"] == "updated"
    extra = await registry.execute("Note_create", {"body": {"title": "temporary"}})
    await registry.execute("Note_bulk_delete", {"body": {"ids": [extra["id"]]}})
    try:
        await registry.execute("Note_get", {"id": extra["id"]})
        raise AssertionError("Bulk delete did not remove record")
    except AgentBlocked:
        pass
    extra = await registry.execute("Note_create", {"body": {"title": "temporary"}})
    await registry.execute("Note_delete", {"id": extra["id"]})
    user_registry = ToolRegistry(
        app, AGENTS["assistant"], AgentContext(user, "s", "r"), token(user)
    )
    assert {d["function"]["name"] for d in await user_registry.definitions()} == {
        "Note_list",
        "Note_get",
    }
    read = await user_registry.execute("Note_get", {"id": note_id})
    assert "secret" not in read, read
    try:
        await user_registry.execute("Note_delete", {"id": note_id})
        raise AssertionError("Unauthorized delete succeeded")
    except AgentBlocked:
        pass
    try:
        await registry.validate("Note_create", {"body": {"title": "hi", "unlisted": True}})
        raise AssertionError("Unknown field accepted")
    except AgentBlocked:
        pass

    class Call:
        type = "function"
        id = "call-1"
        function = SimpleNamespace(name="Note_get", arguments='{"id":%s}' % note_id)

        def model_dump(self, **kwargs):
            return {"type": "function", "id": self.id, "function": vars(self.function)}

    first = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[Call()]),
                finish_reason="tool_calls",
            )
        ],
        usage=None,
    )
    final = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Done", tool_calls=[]), finish_reason="stop"
            )
        ],
        usage=None,
    )
    release = asyncio.Event()
    requests = []
    partial_ready = asyncio.Event()
    allow_final = asyncio.Event()

    create_after_input = False

    async def completion(**kwargs):
        requests.append(kwargs)
        await release.wait()
        if create_after_input and len(requests) == 2:
            answer = json.loads(kwargs["messages"][-1]["content"])
            call = SimpleNamespace(id="create-after-input", function=SimpleNamespace(
                name=answer["tool_name"], arguments=json.dumps(answer["arguments"])))
            return FakeStream(SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[call]), finish_reason="tool_calls")]))
        return FakeStream(first if len(requests) == 1 else final)

    class FakeStream:
        def __init__(self, result):
            self.result = result

        def __aiter__(self):
            async def chunks():
                choice = self.result.choices[0]
                if self.result is final:
                    yield SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content="Do", tool_calls=[]),
                                finish_reason=None,
                            )
                        ],
                        usage=None,
                    )
                    partial_ready.set()
                    await allow_final.wait()
                yield SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(
                                content="ne" if self.result is final else choice.message.content,
                                tool_calls=[
                                    SimpleNamespace(
                                        index=i, id=c.id, type="function", function=c.function
                                    )
                                    for i, c in enumerate(choice.message.tool_calls)
                                ],
                            ),
                            finish_reason=choice.finish_reason,
                        )
                    ],
                    usage=None,
                )

            return chunks()

        async def close(self):
            pass

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=completion))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    agents.AsyncOpenAI = FakeClient
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        endpoint = settings.API_V1_STR + "/agents"
        r = await client.post(
            endpoint + "/sessions", json={"agent_key": "assistant"}, headers=admin_auth
        )
        assert r.status_code == 201, r.text
        id = r.json()["id"]
        url = endpoint + "/sessions/" + id
        assert (await client.get(url, headers=user_auth)).status_code == 404
        assert (await client.delete(url, headers=user_auth)).status_code == 404
        r = await client.post(url + "/messages", json={"content": "read"}, headers=admin_auth)
        assert r.status_code == 202, r.text
        r = await client.post(url + "/messages", json={"content": "duplicate"}, headers=admin_auth)
        assert r.status_code == 409, r.text
        assert (await client.delete(url, headers=admin_auth)).status_code == 409
        release.set()
        await asyncio.wait_for(partial_ready.wait(), 2)
        partial = (await client.get(url, headers=admin_auth)).json()
        assert partial["status"] == "running"
        assert partial["messages"][-1]["payload"]["content"] == "Do"
        assert partial["messages"][-1]["details"]["streaming"] is True

        async def connected():
            return False

        async with AsyncSession(db.engine) as auth_session:
            events = await agents.session_events(
                id, SimpleNamespace(is_disconnected=connected), admin, auth_session
            )
            assert events.media_type == "text/event-stream"
            assert events.headers["x-accel-buffering"] == "no"
            event = await anext(events.body_iterator)
            assert '"content":"Do"' in event and event.startswith("event: session")
            await events.body_iterator.aclose()
        if os.environ.get("ONESITE_AGENT_TEST_CONNECTIONS"):
            from agent_connection_scenario import check_connections
            await check_connections(app, agents, db, url, token(admin))
        allow_final.set()
        await asyncio.gather(*list(agents._running.values()))
        r = await client.get(url, headers=admin_auth)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "idle", data
        assert [m["payload"]["role"] for m in data["messages"]] == [
            "user",
            "assistant",
            "tool",
            "assistant",
        ], data
        assert data["messages"][1]["details"]["calls"]["call-1"]["arguments"] == {"id": note_id}
        assert requests[1]["messages"][-1]["role"] == "tool"
        # Stop a live request and release its lease without repeating an operation.
        release.clear()
        r = await client.post(url + "/messages", json={"content": "again"}, headers=admin_auth)
        assert r.status_code == 202, r.text
        # Wait until the task has actually entered the client before cancellation.
        for _ in range(100):
            if len(requests) >= 3:
                break
            await asyncio.sleep(0.01)
        assert (await client.post(url + "/stop", headers=admin_auth)).status_code == 200
        await asyncio.gather(*list(agents._running.values()), return_exceptions=True)
        data = (await client.get(url, headers=admin_auth)).json()
        assert data["status"] == "failed", data
        # Cancellation during text streaming retains the partial row and marks it interrupted.
        release.set()
        partial_ready.clear()
        allow_final.clear()
        assert (
            await client.post(url + "/messages", json={"content": "partial"}, headers=admin_auth)
        ).status_code == 202
        await asyncio.wait_for(partial_ready.wait(), 2)
        assert (await client.post(url + "/stop", headers=admin_auth)).status_code == 200
        data = (await client.get(url, headers=admin_auth)).json()
        assert data["status"] == "failed"
        assert data["messages"][-1]["payload"]["content"] == "Do"
        assert data["messages"][-1]["details"]["interrupted"] is True
        assert data["messages"][-1]["details"]["streaming"] is False
        # An expired lease closes unmatched tool calls without running the model or tool again.
        async with AsyncSession(db.engine, expire_on_commit=False) as session:
            expired = AgentSession(
                user_id=admin.id,
                agent_key="assistant",
                status="running",
                active_run_id="abandoned",
                expires_at=now() - timedelta(seconds=1),
            )
            session.add(expired)
            await session.flush()
            session.add(
                AgentMessage(
                    session_id=expired.id,
                    seq=1,
                    payload={
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [Call().model_dump()],
                    },
                )
            )
            await session.commit()
        previous_calls = len(requests)
        recovered = (
            await client.get(endpoint + "/sessions/" + expired.id, headers=admin_auth)
        ).json()
        assert recovered["status"] == "failed", recovered
        assert recovered["messages"][-1]["payload"]["tool_call_id"] == "call-1"
        assert recovered["messages"][-1]["details"]["interrupted"]
        assert len(requests) == previous_calls
        # Deleting owned history removes all messages, but never the tool's business data.
        assert (await client.delete(url, headers=admin_auth)).status_code == 204
        assert (await client.get(url, headers=admin_auth)).status_code == 404
        assert (await client.delete(url, headers=admin_auth)).status_code == 404
        async with AsyncSession(db.engine) as session:
            assert await session.get(AgentSession, id) is None
            assert not (
                await session.exec(select(AgentMessage).where(AgentMessage.session_id == id))
            ).all()
        assert (await registry.execute("Note_get", {"id": note_id}))["id"] == note_id
        assert all(
            item["id"] != id
            for item in (await client.get(endpoint + "/sessions", headers=admin_auth)).json()
        )
        # Confirmation is enforced at the registry boundary, including context.api.call.
        config = AGENTS["assistant"]
        config["require_confirmation"] = True
        for name in ("Note_create", "Note_update", "Note_delete", "Note_bulk_delete", "Note_import", "echo"):
            assert registry.requires_confirmation(name), name
        assert not registry.requires_confirmation("Note_get")
        assert not registry.requires_confirmation("Note_list")
        try:
            await registry.call("Note", "delete", {"id": note_id})
            raise AssertionError("Internal API helper bypassed confirmation")
        except AgentBlocked as exc:
            assert "confirmation" in str(exc)
        config["require_confirmation"] = ["Note_delete"]
        assert registry.requires_confirmation("Note_delete")
        assert not registry.requires_confirmation("Note_create")
        config["require_confirmation"] = True

        async def pending_operation(name, arguments, *, expected_name=None, expected_arguments=None):
            requests.clear()
            allow_final.set()
            Call.function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
            r = await client.post(endpoint + "/sessions", json={"agent_key": "assistant"}, headers=admin_auth)
            operation_url = endpoint + "/sessions/" + r.json()["id"]
            r = await client.post(operation_url + "/messages", json={"content": "perform operation"}, headers=admin_auth)
            assert r.status_code == 202, r.text
            for _ in range(200):
                snapshot = (await client.get(operation_url, headers=admin_auth)).json()
                confirmations = [
                    (key, value) for message in snapshot["messages"]
                    for key, value in message["details"].get("interactions", {}).items()
                    if value["status"] == "pending"
                ]
                if confirmations:
                    key, value = confirmations[0]
                    assert value["name"] == (expected_name or name)
                    assert value["arguments"] == (arguments if expected_arguments is None else expected_arguments)
                    assert len(requests) == 1  # the model loop is suspended
                    return operation_url, key
                assert snapshot["status"] == "running", snapshot
                await asyncio.sleep(0.01)
            raise AssertionError("Confirmation never appeared")

        async def settle(operation_url):
            await asyncio.wait_for(asyncio.gather(*list(agents._running.values())), 5)
            snapshot = (await client.get(operation_url, headers=admin_auth)).json()
            assert snapshot["status"] == "idle", snapshot
            return [m for m in snapshot["messages"] if m["payload"]["role"] == "tool"][-1]

        # A form returns typed arguments to the model, which then creates through normal confirmation.
        form_args = {"tool_name": "Note_create", "title": "New note", "fields": ["title"],
                     "arguments": {"body": {"secret": "known"}}}
        relation_form = await registry.input_form({**form_args, "fields": ["owner_id"],
            "arguments": {"body": {"title": "with owner"}}})
        relation = relation_form["ui"]["fields"]["owner_id"]
        assert relation["path"] == "/users"
        assert relation["label_field"]
        assert "User_get" not in registry.tools  # lookup does not expose new model tools
        completed_relation = await registry.input_result(relation_form, {"owner_id": None})
        assert completed_relation["arguments"]["body"]["owner_id"] is None
        assert (await registry.input_form(form_args))["ui"]["fields"] == {}
        # Flat model output is normalized once, including prefilled editable values.
        flat_args = {**form_args, "arguments": {"title": "", "secret": "known"}}
        normalized_form = await registry.input_form(flat_args)
        assert normalized_form["arguments"] == {"body": {"title": "", "secret": "known"}}
        assert normalized_form["initial"] == {"title": ""}
        assert flat_args["arguments"] == {"title": "", "secret": "known"}
        completed = await registry.input_result(normalized_form, {"title": "completed"})
        assert completed["arguments"] == {"body": {"title": "completed", "secret": "known"}}
        update_form = await registry.input_form({**flat_args, "tool_name": "Note_update",
            "arguments": {"id": note_id, "title": "edit"}})
        assert update_form["arguments"] == {"id": note_id, "body": {"title": "edit"}}
        for bad_arguments, expected in (
            ({"body": {}, "title": "PRIVATE_VALUE"}, "additionalProperties"),
            ({"body": {}, "unlisted": "PRIVATE_VALUE"}, "additionalProperties"),
        ):
            try:
                await registry.input_form({**form_args, "arguments": bad_arguments})
                raise AssertionError("Invalid known parameters accepted")
            except AgentBlocked as exc:
                assert expected in str(exc) and "arguments.body" in str(exc)
                assert "PRIVATE_VALUE" not in str(exc)
        try:
            await registry.input_form({**flat_args, "tool_name": "Note_update"})
            raise AssertionError("Missing path ID accepted")
        except AgentBlocked as exc:
            assert "missing required id" in str(exc)
        create_after_input = True
        config["timeout_seconds"] = 1
        operation_url, key = await pending_operation("request_input", flat_args,
            expected_name="Note_create", expected_arguments=normalized_form["arguments"])
        snapshot = (await client.get(operation_url, headers=admin_auth)).json()
        form = snapshot["messages"][1]["details"]["interactions"][key]
        assert form["kind"] == "form" and list(form["schema"]["properties"]) == ["title"]
        form_url = operation_url + "/interactions/" + key
        # Owner isolation, server validation and action separation; invalid answers leave the form pending.
        assert (await client.post(form_url, json={"action": "submit", "values": {"title": "form-created"}}, headers=user_auth)).status_code == 404
        for body in ({"action": "approve"}, {"action": "submit", "values": {}},
                     {"action": "submit", "values": {"title": 123}},
                     {"action": "submit", "values": {"title": "x", "secret": "changed"}}):
            assert (await client.post(form_url, json=body, headers=admin_auth)).status_code == 422
        await asyncio.sleep(1.1)
        assert len(requests) == 1  # Waiting does not consume the one-second execution budget.
        assert (await client.get(operation_url, headers=admin_auth)).json()["status"] == "running"
        responses = await asyncio.gather(*[client.post(form_url,
            json={"action": "submit", "values": {"title": "form-created"}}, headers=admin_auth) for _ in range(2)])
        assert sorted(response.status_code for response in responses) == [200, 409]
        for _ in range(200):
            snapshot = (await client.get(operation_url, headers=admin_auth)).json()
            pending = [(key, value) for message in snapshot["messages"]
                       for key, value in message["details"].get("interactions", {}).items()
                       if value["status"] == "pending" and value.get("kind") == "confirmation"]
            if pending:
                break
            await asyncio.sleep(0.01)
        assert pending, snapshot
        confirmation_id, confirmation = pending[0]
        assert confirmation["arguments"] == {"body": {"title": "form-created", "secret": "known"}}
        assert not any(row["title"] == "form-created" for row in (await registry.execute("Note_list", {}))["items"])
        assert (await client.post(operation_url + "/interactions/" + confirmation_id,
            json={"action": "approve"}, headers=admin_auth)).status_code == 200
        result = await settle(operation_url)
        assert result["details"]["success"] is True, result
        assert json.loads(result["payload"]["content"])["title"] == "form-created"
        create_after_input = False
        config["timeout_seconds"] = 120

        # Active execution timeout resumes after submitting a form, even if the next model stalls.
        config["timeout_seconds"] = 1
        operation_url, key = await pending_operation("request_input", form_args,
            expected_name="Note_create", expected_arguments=form_args["arguments"])
        allow_final.clear()
        assert (await client.post(operation_url + "/interactions/" + key,
            json={"action": "submit", "values": {"title": "timeout after input"}}, headers=admin_auth)).status_code == 200
        await asyncio.wait_for(asyncio.gather(*list(agents._running.values())), 5)
        snapshot = (await client.get(operation_url, headers=admin_auth)).json()
        assert snapshot["status"] == "failed" and "timed out" in snapshot["error"], snapshot
        config["timeout_seconds"] = 120
        allow_final.set()

        # Custom tools use root parameters and retain JSON types (including false, zero and null).
        typed_args = {"tool_name": "echo", "title": "Typed fields", "fields": ["text", "enabled", "count", "tag", "when", "meta"], "arguments": {}}
        operation_url, key = await pending_operation("request_input", typed_args,
            expected_name="echo", expected_arguments={})
        values = {"text": "typed", "enabled": False, "count": 0, "tag": "b", "when": None, "meta": {"a": [1, 2]}}
        form_url = operation_url + "/interactions/" + key
        assert (await client.post(form_url, json={"action": "submit", "values": {**values, "tag": "invalid"}}, headers=admin_auth)).status_code == 422
        assert (await client.post(form_url, json={"action": "submit", "values": values}, headers=admin_auth)).status_code == 200
        result = await settle(operation_url)
        assert json.loads(result["payload"]["content"])["arguments"] == values

        # Cancelling a form yields a tool result and never calls the target API.
        operation_url, key = await pending_operation("request_input", form_args,
            expected_name="Note_create", expected_arguments=form_args["arguments"])
        assert (await client.post(operation_url + "/interactions/" + key,
            json={"action": "reject"}, headers=admin_auth)).status_code == 200
        assert (await settle(operation_url))["details"]["success"] is False

        # The same lifecycle invalidates stopped and expired forms.
        for expired in (False, True):
            if expired:
                config["user_input_timeout_seconds"] = 1
            operation_url, key = await pending_operation("request_input", form_args,
                expected_name="Note_create", expected_arguments=form_args["arguments"])
            if not expired:
                await client.post(operation_url + "/stop", headers=admin_auth)
            await asyncio.wait_for(asyncio.gather(*list(agents._running.values())), 5)
            assert (await client.post(operation_url + "/interactions/" + key,
                json={"action": "submit", "values": {"title": "late"}}, headers=admin_auth)).status_code == 409
            config["user_input_timeout_seconds"] = 1800

        # Schema extraction never exposes inaccessible fields, arbitrary targets or incomplete known IDs.
        for invalid in (
            {**form_args, "tool_name": "unregistered"},
            {**form_args, "fields": ["unlisted"]},
            {**form_args, "arguments": {"body": {"unlisted": "hidden"}}},
            {**form_args, "tool_name": "Note_update"},
        ):
            try:
                await registry.input_form(invalid)
                raise AssertionError("Invalid form accepted")
            except AgentBlocked:
                pass
        try:
            await user_registry.input_form(form_args)
            raise AssertionError("Unauthorized form accepted")
        except AgentBlocked:
            pass

        # Current field permissions are checked again before accepting submitted values.
        operation_url, key = await pending_operation("request_input", form_args,
            expected_name="Note_create", expected_arguments=form_args["arguments"])
        from app.core.agent_tools import MODELS
        previous = MODELS["Note"]["fields"]["title"]["admin"]
        MODELS["Note"]["fields"]["title"]["admin"] = "r"
        assert (await client.post(operation_url + "/interactions/" + key,
            json={"action": "submit", "values": {"title": "forbidden"}}, headers=admin_auth)).status_code == 422
        MODELS["Note"]["fields"]["title"]["admin"] = previous
        await client.post(operation_url + "/stop", headers=admin_auth)

        # The confirmation uses final hook-adjusted arguments, not the model's original input.
        original_load_hooks = agents.load_hooks
        async def replace_title(event, context):
            return ToolArgumentsOverride({"body": {"title": "approved create"}})
        agents.load_hooks = lambda config: {"before_tool": replace_title}
        operation_url, key = await pending_operation("Note_create", {"body": {"title": "model proposal"}},
            expected_arguments={"body": {"title": "approved create"}})
        agents.load_hooks = original_load_hooks
        assert not any(row["title"] == "approved create" for row in (await registry.execute("Note_list", {}))["items"])
        decision_url = operation_url + "/confirmations/" + key
        assert (await client.post(decision_url, json={"approved": True}, headers=user_auth)).status_code == 404
        assert (await client.post(decision_url, json={"approved": "yes"}, headers=admin_auth)).status_code == 422
        decisions = await asyncio.gather(*[
            client.post(decision_url, json={"approved": True}, headers=admin_auth) for _ in range(2)
        ])
        assert sorted(r.status_code for r in decisions) == [200, 409]
        result = await settle(operation_url)
        assert result["details"]["success"] is True
        approved_id = json.loads(result["payload"]["content"])["id"]

        operation_url, key = await pending_operation("Note_update", {"id": approved_id, "body": {"title": "approved update"}})
        assert (await registry.execute("Note_get", {"id": approved_id}))["title"] == "approved create"
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 200
        assert (await settle(operation_url))["details"]["success"] is True
        assert (await registry.execute("Note_get", {"id": approved_id}))["title"] == "approved update"

        # An unconfirmed custom wrapper cannot bypass confirmation on a nested API write.
        import app.agent_tools.echo as echo_module
        original_echo = echo_module.echo
        async def nested_delete(args, context):
            return await context.api.call("Note", "delete", {"id": approved_id})
        nested_delete.agent_args_model = original_echo.agent_args_model
        nested_delete.agent_roles = original_echo.agent_roles
        echo_module.echo = nested_delete
        config["require_confirmation"] = ["delete"]
        operation_url, key = await pending_operation("echo", {"text": "delete"},
            expected_name="Note_delete", expected_arguments={"id": approved_id})
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": False}, headers=admin_auth)).status_code == 200
        assert (await settle(operation_url))["details"]["success"] is False
        assert (await registry.execute("Note_get", {"id": approved_id}))["id"] == approved_id
        echo_module.echo = original_echo
        config["require_confirmation"] = True

        operation_url, key = await pending_operation("Note_delete", {"id": approved_id})
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": False}, headers=admin_auth)).status_code == 200
        result = await settle(operation_url)
        assert result["details"]["success"] is False and "rejected" in result["payload"]["content"]
        assert (await registry.execute("Note_get", {"id": approved_id}))["id"] == approved_id

        operation_url, key = await pending_operation("Note_import", {"file_content": "title,secret\nimport confirmed,private\n"})
        assert not any(row["title"] == "import confirmed" for row in (await registry.execute("Note_list", {}))["items"])
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 200
        result = await settle(operation_url)
        assert result["details"]["success"] is True, result
        assert json.loads(result["payload"]["content"])["created"] == 1, result

        operation_url, key = await pending_operation("Note_bulk_delete", {"body": {"ids": [approved_id]}})
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 200
        assert (await settle(operation_url))["details"]["success"] is True
        assert not any(row["id"] == approved_id for row in (await registry.execute("Note_list", {}))["items"])

        # Stop and expired leases invalidate pending approvals without executing a delete.
        operation_url, key = await pending_operation("Note_delete", {"id": note_id})
        assert (await client.post(operation_url + "/stop", headers=admin_auth)).status_code == 200
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 409
        snapshot = (await client.get(operation_url, headers=admin_auth)).json()
        assert snapshot["messages"][1]["details"]["interactions"][key]["status"] == "interrupted"
        assert (await registry.execute("Note_get", {"id": note_id}))["id"] == note_id

        config["user_input_timeout_seconds"] = 1
        operation_url, key = await pending_operation("Note_delete", {"id": note_id})
        await asyncio.wait_for(asyncio.gather(*list(agents._running.values())), 5)
        snapshot = (await client.get(operation_url, headers=admin_auth)).json()
        assert snapshot["status"] == "failed" and "timed out" in snapshot["error"]
        assert snapshot["messages"][1]["details"]["interactions"][key]["status"] == "interrupted"
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 409
        assert (await registry.execute("Note_get", {"id": note_id}))["id"] == note_id
        config["user_input_timeout_seconds"] = 120

        operation_url, key = await pending_operation("Note_delete", {"id": note_id})
        async with AsyncSession(db.engine) as session:
            item = await session.get(AgentSession, operation_url.rsplit("/", 1)[1])
            item.expires_at = now() - timedelta(seconds=1)
            session.add(item)
            await session.commit()
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 409
        await asyncio.wait_for(asyncio.gather(*list(agents._running.values())), 5)
        assert (await registry.execute("Note_get", {"id": note_id}))["id"] == note_id

        # Old confirmation records and endpoint remain compatible with the shared wait path.
        operation_url, key = await pending_operation("Note_delete", {"id": note_id})
        async with AsyncSession(db.engine) as session:
            messages = await agents.rows(session, operation_url.rsplit("/", 1)[1])
            message = messages[1]
            records = message.details["interactions"]
            records[key].pop("kind")
            message.details = {key: value for key, value in message.details.items() if key != "interactions"}
            message.details = {**message.details, "confirmations": records}
            session.add(message)
            await session.commit()
        assert (await client.post(operation_url + "/confirmations/" + key,
            json={"approved": False}, headers=admin_auth)).status_code == 200
        assert (await settle(operation_url))["details"]["success"] is False

        # Approval cannot override role changes made while the user was deciding.
        operation_url, key = await pending_operation("Note_delete", {"id": note_id})
        # Permissions are refreshed from the DB, not cached with the session.
        async with AsyncSession(db.engine) as session:
            current = await session.get(User, admin.id)
            current.role = UserRole.USER
            session.add(current)
            await session.commit()
        assert (await client.post(operation_url + "/confirmations/" + key, json={"approved": True}, headers=admin_auth)).status_code == 200
        result = await settle(operation_url)
        assert result["details"]["success"] is False
        config["require_confirmation"] = False
        try:
            await registry.execute("Note_delete", {"id": note_id})
            raise AssertionError("Stale role permitted delete")
        except AgentBlocked:
            pass
    await db.engine.dispose()


asyncio.run(main())
print("Generated agent API scenario passed")
