"""Built-in agent protocol, hook boundaries and optional code generation."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from onesite.codegen.agents import validate_agents_config
from onesite.codegen.config import SiteConfigError
from onesite.main import app

TEMPLATES = Path(__file__).parents[1] / "src/onesite/templates/codegen"


@pytest.fixture
def runtime():
    spec = importlib.util.spec_from_loader("agent_under_test", loader=None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(
        compile((TEMPLATES / "agent_runtime.py.j2").read_text(), "agent.py", "exec"),
        module.__dict__,
    )
    yield module
    sys.modules.pop(spec.name, None)


class Call:
    type = "function"

    def __init__(self, id, name="A_get", arguments='{"id":1}'):
        self.id = id
        self.function = SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self, **kwargs):
        return {"id": self.id, "type": self.type, "function": vars(self.function)}


def response(*calls, finish=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None if calls else "Done", tool_calls=list(calls)),
                finish_reason=finish or ("tool_calls" if calls else "stop"),
            )
        ],
        usage=None,
    )


class FakeStream:
    def __init__(self, result):
        self.result = result
        self.closed = False

    def __aiter__(self):
        async def chunks():
            choice = self.result.choices[0]
            calls = [
                SimpleNamespace(index=index, id=call.id, type="function", function=call.function)
                for index, call in enumerate(choice.message.tool_calls)
            ]
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=choice.message.content, tool_calls=calls),
                        finish_reason=choice.finish_reason,
                    )
                ],
                usage=None,
            )

        return chunks()

    async def close(self):
        self.closed = True


async def execute(runtime, responses, hooks=None, registry=None, steps=4):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(side_effect=[FakeStream(r) for r in responses])
            )
        )
    )
    registry = registry or SimpleNamespace(
        definitions=AsyncMock(return_value=[]),
        validate=AsyncMock(),
        execute=AsyncMock(return_value={"id": 1}),
    )
    events = []

    async def emit(payload, metadata):
        events.append(copy.deepcopy((payload, metadata)))

    await runtime.run_agent(
        client=client,
        config={"model": "test", "instructions": "system", "max_steps": steps},
        messages=[{"role": "user", "content": "hello"}],
        registry=registry,
        context=runtime.AgentContext(None, "s", "r"),
        emit=emit,
        check=AsyncMock(),
        hooks=hooks,
    )
    return client, registry, events


@pytest.mark.asyncio
async def test_all_tools_finish_before_next_model_call(runtime):
    client, registry, events = await execute(
        runtime, [response(Call("c1"), Call("c2")), response()]
    )
    assert registry.execute.await_count == 2
    second = client.chat.completions.create.call_args_list[1].kwargs["messages"]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "tool", "tool"]
    assert [m["tool_call_id"] for m in second[-2:]] == ["c1", "c2"]
    assert events[1][0] is None  # execution journal precedes first side effect/result
    assert events[-1][0]["content"] == "Done"


@pytest.mark.asyncio
async def test_hook_arguments_revalidated_and_results_transformed(runtime):
    order = []

    async def before(event, context):
        order.append("before")
        return runtime.ToolArgumentsOverride({"id": 2})

    async def after(event, context):
        assert event.success
        order.append("after")
        return runtime.ToolResultOverride({"safe": True})

    _, registry, events = await execute(
        runtime, [response(Call("c")), response()], {"before_tool": before, "after_tool": after}
    )
    assert registry.validate.call_args_list[-1].args == ("A_get", {"id": 2})
    assert registry.execute.call_args.args == ("A_get", {"id": 2})
    assert json.loads(events[2][0]["content"]) == {"safe": True}
    assert order == ["before", "after"]


@pytest.mark.asyncio
async def test_blocked_tool_still_has_protocol_result(runtime):
    async def blocked(event, context):
        raise runtime.AgentBlocked("No deletion")

    _, registry, events = await execute(
        runtime, [response(Call("c")), response()], {"before_tool": blocked}
    )
    registry.execute.assert_not_called()
    assert events[1][0]["tool_call_id"] == "c"
    assert "No deletion" in events[1][0]["content"]


@pytest.mark.asyncio
async def test_broken_hook_never_executes_tool(runtime):
    async def broken(event, context):
        raise ValueError("hook broke")

    registry = SimpleNamespace(
        definitions=AsyncMock(return_value=[]), validate=AsyncMock(), execute=AsyncMock()
    )
    with pytest.raises(ValueError, match="hook broke"):
        await execute(runtime, [response(Call("c"))], {"before_tool": broken}, registry)
    registry.execute.assert_not_called()


@pytest.mark.asyncio
async def test_after_tool_observes_execution_failure(runtime):
    registry = SimpleNamespace(
        definitions=AsyncMock(return_value=[]),
        validate=AsyncMock(),
        execute=AsyncMock(side_effect=RuntimeError("secret exception")),
    )
    after = AsyncMock()
    after.return_value = None
    _, _, events = await execute(
        runtime, [response(Call("c")), response()], {"after_tool": after}, registry
    )
    assert after.call_args.args[0].success is False
    assert "secret exception" not in str(events)


@pytest.mark.asyncio
async def test_model_hook_does_not_modify_persisted_history(runtime):
    async def before(event, context):
        event.messages[-1]["content"] = "private context"
        return runtime.ModelRequestOverride(messages=event.messages)

    client, _, _ = await execute(runtime, [response()], {"before_model": before})
    assert (
        client.chat.completions.create.call_args.kwargs["messages"][-1]["content"]
        == "private context"
    )


@pytest.mark.asyncio
async def test_step_limit_and_malformed_arguments(runtime):
    with pytest.raises(runtime.AgentBlocked, match="Maximum"):
        await execute(runtime, [response(Call("c", arguments="{"))], steps=1)


@pytest.mark.asyncio
async def test_error_hook_failure_does_not_recurse(runtime):
    error = AsyncMock(side_effect=RuntimeError("logging failed"))
    with pytest.raises(RuntimeError, match="Model did not finish"):
        await execute(runtime, [response(finish="length")], {"on_error": error})
    assert error.await_count == 1


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"a": {"model": "x", "hooks": {"unknown": "agent_hooks.a"}}},
        {"a": {"model": "x", "model_tools": {"A": ["drop"]}}},
        {"a": {"model": "x", "custom_tools": ["../bad"]}},
        {"a": {"model": "x", "custom_tools": ["request_input"]}},
        {"a": {"model": "x", "user_input_timeout_seconds": 0}},
        {"a": {"model": "x", "max_steps": 0}},
        {"a": {"model": "x", "require_confirmation": ["typo_delete"]}},
        {"a": {"model": "x", "require_confirmation": {"delete": True}}},
    ],
)
def test_invalid_config(value):
    with pytest.raises(SiteConfigError):
        validate_agents_config({"agents": value})


def test_confirmation_config_defaults_and_selectors():
    config = {"agents": {"a": {"model": "test"}}}
    validate_agents_config(config)
    assert config["agents"]["a"]["require_confirmation"] is False
    assert config["agents"]["a"]["user_input_timeout_seconds"] == 1800
    config = {"agents": {"a": {
        "model": "test", "model_tools": {"Note": ["crud", "import", "bulk_delete"]},
        "custom_tools": ["publish"],
        "require_confirmation": ["cud", "bulk_delete", "import", "Note_delete", "publish"],
    }}}
    validate_agents_config(config)
    assert config["agents"]["a"]["require_confirmation"] == [
        "create", "update", "delete", "bulk_delete", "import", "Note_delete", "publish",
    ]
    validate_agents_config(config)  # normalization is idempotent


def test_import_tool_requires_importable_model(tmp_path):
    from onesite.codegen.agents import generate_agents

    config = {"agents": {"a": {"model": "test", "model_tools": {"Note": ["import"]}}}}
    validate_agents_config(config)
    with pytest.raises(SiteConfigError, match="must enable importable"):
        generate_agents(config, [{"name": "Note", "module_name": "note"}], tmp_path,
                        tmp_path / "generated/backend")


def test_codegen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "AgentApp"])
    assert result.exit_code == 0, result.output
    project = tmp_path / "AgentApp"
    (project / "site_config.py").write_text(
        'from onesite.config import SiteConfig\nconfig = SiteConfig(agents={"assistant": {"model":"test", "model_tools":{"User":["list","get"]}, "custom_tools":["lookup"], "hooks":{"before_tool":"agent_hooks.check"}}})\n'
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    backend = project / "generated/backend"
    assert 'prefix="/agents"' in (backend / "app/api/api.py").read_text()
    for filename in ("agent.py", "agent_tools.py", "agent_models.py"):
        compile((backend / "app/core" / filename).read_text(), filename, "exec")
    endpoint = (backend / "app/api/endpoints/agents.py").read_text()
    compile(endpoint, "agents.py", "exec")
    backend_config = (backend / "app/core/config.py").read_text()
    compile(backend_config, "config.py", "exec")
    assert 'AGENT_BASE_URL: str = "https://api.openai.com/v1"' in backend_config
    assert "AGENT_API_KEY: Optional[str] = None" in backend_config
    assert 'AGENT_MODEL: str = "test"' in backend_config
    assert '"base_url": settings.AGENT_BASE_URL' in endpoint
    assert '"model": settings.AGENT_MODEL' in endpoint
    backend_env = backend / ".env"
    environment = backend_env.read_text()
    assert "AGENT_BASE_URL=https://api.openai.com/v1" in environment
    assert "AGENT_MODEL=test" in environment
    assert "AGENT_API_KEY=" in environment
    backend_env.write_text(environment.replace("AGENT_API_KEY=", "AGENT_API_KEY=test-secret"))
    assert "AgentPage" in (project / "generated/frontend/src/Routes.tsx").read_text()
    assert '"/agent"' in (project / "generated/frontend/src/Menu.tsx").read_text()
    source = project / "app/agent_hooks.py"
    source.write_text('async def check(event, context):\n    """preserved"""\n    return None\n')
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    assert "preserved" in source.read_text()
    assert "AGENT_API_KEY=test-secret" in backend_env.read_text()
    # Disabling removes exposed routes and replaceable runtime, never source or stored data.
    (project / "site_config.py").write_text(
        "from onesite.config import SiteConfig\nconfig = SiteConfig()\n"
    )
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    assert "AgentPage" not in (project / "generated/frontend/src/Routes.tsx").read_text()
    assert not (backend / "app/core/agent.py").exists()
    assert source.exists()


def test_generated_api_with_sqlite(tmp_path):
    import os
    import subprocess

    for dependency in ("openai", "jsonschema", "httpx", "jose", "pydantic_settings"):
        if importlib.util.find_spec(dependency) is None:
            pytest.skip("Generated backend dependencies required for API integration test")
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/support/agent_scenario.py"), str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_composite_key_model_preserves_api_identity(tmp_path):
    from onesite.codegen.agents import generate_agents

    config = {"agents": {"assistant": {"model": "test", "model_tools": {"Point": ["get"]}}}}
    validate_agents_config(config)
    model = {
        "name": "Point",
        "module_name": "point",
        "table_name": "point",
        "role_permissions": {"admin": "crud"},
        "fields": [{"name": "device_id", "permissions": "r"}, {"name": "name", "permissions": "r"}],
    }
    backend = tmp_path / "generated/backend"
    generate_agents(config, [model], tmp_path, backend)
    import ast

    tree = ast.parse((backend / "app/core/agent_tools.py").read_text())
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign) and node.targets[0].id == "MODELS"
    )
    metadata = json.loads(ast.literal_eval(assignment.value.args[0]))
    assert metadata["Point"]["fields"]["id"]["admin"] == "r"


@pytest.mark.asyncio
async def test_streamed_text_is_emitted_before_completion(runtime):
    import asyncio

    started = asyncio.Event()
    finish = asyncio.Event()
    partials = []
    saved = []

    class Stream:
        closed = False

        async def close(self):
            self.closed = True

        def __aiter__(self):
            async def chunks():
                yield SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(content="你", tool_calls=[]), finish_reason=None
                        )
                    ],
                    usage=None,
                )
                started.set()
                await finish.wait()
                yield SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(content="好", tool_calls=[]), finish_reason="stop"
                        )
                    ],
                    usage=None,
                )

            return chunks()

    stream = Stream()

    async def partial(payload):
        partials.append(payload)

    async def emit(payload, metadata):
        saved.append(payload)

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=stream)))
    )
    task = asyncio.create_task(
        runtime.run_agent(
            client=client,
            config={"model": "test", "instructions": "", "max_steps": 1},
            messages=[],
            registry=SimpleNamespace(definitions=AsyncMock(return_value=[])),
            context=runtime.AgentContext(None, "s", "r"),
            emit=emit,
            check=AsyncMock(),
            emit_partial=partial,
        )
    )
    await asyncio.wait_for(started.wait(), 1)
    assert partials == [{"role": "assistant", "content": "你"}]
    assert not saved and not task.done()
    finish.set()
    await task
    assert saved == [{"role": "assistant", "content": "你好"}]
    assert stream.closed
    assert client.chat.completions.create.call_args.kwargs["stream"] is True


@pytest.mark.asyncio
async def test_interleaved_tool_fragments_and_usage(runtime):
    def fragment(index, id=None, name=None, args=None):
        return SimpleNamespace(
            index=index, id=id, type=None, function=SimpleNamespace(name=name, arguments=args)
        )

    chunks = [
        ([fragment(1, "b", "A_get", '{"id":'), fragment(0, "a", "A_get", "{")], None),
        ([fragment(0, args='"id":1}'), fragment(1, args="2}")], "tool_calls"),
    ]

    class Stream:
        closed = False

        async def close(self):
            self.closed = True

        def __aiter__(self):
            async def items():
                for calls, reason in chunks:
                    yield SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=None, tool_calls=calls),
                                finish_reason=reason,
                            )
                        ],
                        usage=None,
                    )
                yield SimpleNamespace(
                    choices=[], usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 12})
                )

            return items()

    stream = Stream()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=stream)))
    )
    payload, calls, usage = await runtime.stream_completion(client, {}, AsyncMock(), AsyncMock())
    assert [call["id"] for call in calls] == ["a", "b"]
    assert [json.loads(call["function"]["arguments"]) for call in calls] == [{"id": 1}, {"id": 2}]
    assert payload["tool_calls"] == calls and usage == {"total_tokens": 12}
    assert stream.closed


@pytest.mark.asyncio
async def test_truncated_stream_cannot_execute_tools(runtime):
    stream = FakeStream(response(Call("partial"), finish="length"))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=stream)))
    )
    with pytest.raises(RuntimeError, match="Model did not finish"):
        await runtime.stream_completion(client, {}, AsyncMock(), AsyncMock())
    assert stream.closed
