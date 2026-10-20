"""Scheduled task source ownership and background execution generation."""

import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.codegen.assets import _sync_scheduled_tasks
from onesite.codegen.config import SiteConfigError, validate_scheduled_tasks_config
from onesite.main import app


TEMPLATE_DIR = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def _tasks():
    config = {
        "scheduled_tasks": [
            {
                "name": "daily_summary",
                "title": "Daily summary",
                "schedule": {"type": "interval", "seconds": 300},
                "params": [
                    {"name": "region", "type": "str", "default": "cn"},
                    {"name": "include_inactive", "type": "bool", "default": False},
                ],
            }
        ]
    }
    validate_scheduled_tasks_config(config)
    return config["scheduled_tasks"]


def test_new_schedule_shape_is_normalized():
    task = _tasks()[0]
    assert task["interval"] == 300
    assert task["cron"] == ""
    assert task["params"]["region"]["value"] == "cn"
    assert task["manual_permissions"] == ["admin", "developer"]
    assert task["overlap"] == "skip"


def test_legacy_schedule_shape_remains_supported():
    config = {
        "scheduled_tasks": [
            {
                "name": "cleanup",
                "cron": "0 2 * * *",
                "interval": 0,
                "params": {
                    "days": {"type": "number", "default": 30, "label": "Days"}
                },
            }
        ]
    }
    validate_scheduled_tasks_config(config)
    task = config["scheduled_tasks"][0]
    assert task["schedule"] == {"type": "cron", "cron": "0 2 * * *"}
    assert task["params"]["days"]["value"] == 30


@pytest.mark.parametrize(
    ("configured_type", "normalized_type"),
    [
        ("str", "str"),
        ("string", "str"),
        ("bool", "bool"),
        ("boolean", "bool"),
        ("multi_select", "multi_select"),
        ("list", "multi_select"),
    ],
)
@pytest.mark.parametrize("params_shape", ["array", "object"])
def test_scheduled_param_type_aliases_are_normalized(
    configured_type, normalized_type, params_shape
):
    param = {"name": "value", "type": configured_type} if params_shape == "array" else None
    params = [param] if params_shape == "array" else {"value": {"type": configured_type}}
    config = {
        "scheduled_tasks": [{"name": "run", "interval": 10, "params": params}]
    }
    validate_scheduled_tasks_config(config)
    assert config["scheduled_tasks"][0]["params"]["value"]["type"] == normalized_type


def test_scheduled_handler_is_scaffolded_and_mirrored(tmp_path):
    (tmp_path / "app").mkdir()
    backend = tmp_path / "generated" / "backend"
    _sync_scheduled_tasks(tmp_path, backend, _tasks())

    source = tmp_path / "app" / "tasks" / "daily_summary.py"
    generated = backend / "app" / "tasks" / "daily_summary.py"
    assert source.exists()
    assert generated.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "context: ScheduledTaskContext" in source.read_text(encoding="utf-8")


def test_legacy_generated_handler_is_migrated_without_requiring_context(tmp_path):
    backend = tmp_path / "generated" / "backend"
    legacy = backend / "app" / "tasks" / "daily_summary.py"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        "from app.core.scheduler import task_registry\n\n"
        "async def daily_summary(*, region, include_inactive):\n    return region\n\n"
        "# 注册任务\n"
        "task_registry.register({\n"
        "    'name': 'daily_summary',\n"
        "    'func': 'app.tasks.daily_summary:daily_summary',\n"
        "    'interval': 300,\n"
        "})\n",
        encoding="utf-8",
    )
    _sync_scheduled_tasks(tmp_path, backend, _tasks())
    source = tmp_path / "app" / "tasks" / "daily_summary.py"
    assert source.exists()
    source_text = source.read_text(encoding="utf-8")
    assert "return region" in source_text
    assert "task_registry" not in source_text
    assert "注册任务" not in source_text
    assert (backend / "app" / "tasks" / "daily_summary.py").read_text(encoding="utf-8") == source_text


def test_existing_developer_task_is_cleaned_of_old_registration(tmp_path):
    source = tmp_path / "app" / "tasks" / "daily_summary.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from app.core.scheduler import task_registry\n\n"
        "async def daily_summary(*, region, include_inactive):\n"
        "    return region\n\n"
        "# Task registration\n"
        "task_registry.register({'name': 'daily_summary'})\n",
        encoding="utf-8",
    )
    _sync_scheduled_tasks(tmp_path, tmp_path / "generated" / "backend", _tasks())
    cleaned = source.read_text(encoding="utf-8")
    assert "async def daily_summary" in cleaned
    assert "task_registry" not in cleaned
    assert "Task registration" not in cleaned


@pytest.mark.parametrize(
    ("tasks", "message"),
    [
        ({}, "must be a JSON array"),
        ([{"name": "bad-name", "interval": 10}], "valid Python identifier"),
        ([{"name": "run", "interval": 0, "cron": "bad"}], "five-part cron"),
        ([{"name": "run", "schedule": {"type": "interval", "seconds": 0}}], "positive integer"),
        ([{"name": "run", "interval": 10, "overlap": "replace"}], "overlap"),
        ([{"name": "run", "interval": 10, "params": [{"name": "file", "type": "files"}]}], "not supported"),
        ([{"name": "run", "interval": 10, "params": {"value": {"type": []}}}], "type must be"),
    ],
)
def test_invalid_scheduled_task_config_is_rejected(tasks, message):
    config = json.loads(json.dumps({"scheduled_tasks": tasks}))
    with pytest.raises(SiteConfigError, match=message):
        validate_scheduled_tasks_config(config)


def test_generated_scheduled_task_modules_compile():
    tasks = _tasks()
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    contexts = {
        "scheduled_task_handler.py.j2": {"task": tasks[0]},
        "scheduled_task_bindings.py.j2": {
            "tasks": tasks,
            "tasks_json": json.dumps(tasks, ensure_ascii=False),
        },
        "scheduled_task_runtime.py.j2": {},
        "scheduled_task_execution_handler.py.j2": {},
        "app_tasks_api.py.j2": {},
        "scheduler.py.j2": {},
    }
    for template_name, context in contexts.items():
        rendered = env.get_template(template_name).render(context)
        compile(rendered, template_name, "exec")


def test_site_sync_generates_background_scheduled_task_feature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ScheduledApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "ScheduledApp"
    config_path = project / "site_config.py"
    config_path.write_text(
        "from onesite.config import SiteConfig\n"
        f"config = SiteConfig(scheduled_tasks={_tasks()!r})\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    backend = project / "generated" / "backend" / "app"
    assert (project / "app" / "tasks" / "daily_summary.py").exists()
    assert (backend / "tasks" / "daily_summary.py").exists()
    assert (backend / "core" / "background_execution.py").exists()
    assert (backend / "core" / "background_execution_cleanup.py").exists()
    db_source = (backend / "core" / "db.py").read_text(encoding="utf-8")
    assert "import app.core.background_execution" in db_source
    assert "ALTER COLUMN %I TYPE TIMESTAMPTZ" in db_source
    execution_model = (backend / "core" / "background_execution.py").read_text(
        encoding="utf-8"
    )
    assert execution_model.count("DateTime(timezone=True)") == 3
    assert (backend / "core" / "scheduled_task_bindings.py").exists()
    assert (backend / "core" / "scheduled_task_runtime.py").exists()
    assert (backend / "handlers" / "scheduled_task_execution.py").exists()
    assert (backend / "api" / "endpoints" / "tasks.py").exists()
    assert (backend / "api" / "endpoints" / "task_center.py").exists()
    frontend = project / "generated" / "frontend" / "src"
    assert (frontend / "pages" / "TaskCenter.tsx").exists()
    assert "scheduled_task" in (frontend / "pages" / "TaskCenter.tsx").read_text(
        encoding="utf-8"
    )
    for python_file in backend.rglob("*.py"):
        compile(python_file.read_text(encoding="utf-8"), str(python_file), "exec")


def test_tools_and_schedules_share_background_execution_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "CombinedApp"])
    assert created.exit_code == 0, created.output
    project = tmp_path / "CombinedApp"
    config_path = project / "site_config.py"
    config_path.write_text(
        "from onesite.config import SiteConfig\n"
        "config = SiteConfig(\n"
        f"    scheduled_tasks={_tasks()!r},\n"
        "    tools=[{'name': 'recalculate', 'inputs': [{'name': 'count', 'type': 'number', 'number_kind': 'int'}]}],\n"
        ")\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    backend = project / "generated" / "backend" / "app"
    assert (backend / "core" / "background_execution.py").exists()
    assert not (backend / "core" / "tool_execution.py").exists()
    handlers = (backend / "handlers" / "__init__.py").read_text(encoding="utf-8")
    assert "tool_execution" in handlers
    assert "scheduled_task_execution" in handlers
