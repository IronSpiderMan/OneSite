"""Configuration-driven project tools generation."""

import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.codegen.assets import _sync_tools
from onesite.codegen.config import SiteConfigError, validate_tools_config
from onesite.codegen.i18n import generate_locale_files
from onesite.main import app


TEMPLATE_DIR = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def _tools():
    config = {
        "tools": [
            {
                "name": "merge_reports",
                "title": "Merge reports",
                "inputs": [
                    {"name": "copies", "type": "number", "number_kind": "int", "required": True},
                    {"name": "files", "type": "files", "required": True, "accept": [".csv"]},
                ],
                "result": {"type": "file"},
            }
        ]
    }
    validate_tools_config(config)
    return config["tools"]


def test_tool_handler_is_scaffolded_and_mirrored(tmp_path):
    tools = _tools()
    backend = tmp_path / "generated" / "backend"

    _sync_tools(tmp_path, backend, tools)

    source = tmp_path / "app" / "tools" / "merge_reports.py"
    generated = backend / "app" / "tools" / "merge_reports.py"
    assert source.exists()
    assert generated.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "async def merge_reports" in source.read_text(encoding="utf-8")
    assert "files: list[str]" in source.read_text(encoding="utf-8")


def test_existing_tool_source_is_not_overwritten(tmp_path):
    source_dir = tmp_path / "app" / "tools"
    source_dir.mkdir(parents=True)
    source = source_dir / "merge_reports.py"
    source.write_text(
        "async def merge_reports(*, copies, files, context):\n    return {'count': copies}\n",
        encoding="utf-8",
    )

    _sync_tools(tmp_path, tmp_path / "generated" / "backend", _tools())

    assert "return {'count': copies}" in source.read_text(encoding="utf-8")
    assert (tmp_path / "generated" / "backend" / "app" / "tools" / "merge_reports.py").read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_tool_handler_signature_must_follow_config(tmp_path):
    source_dir = tmp_path / "app" / "tools"
    source_dir.mkdir(parents=True)
    (source_dir / "merge_reports.py").write_text(
        "async def merge_reports(*, copies, context):\n    pass\n",
        encoding="utf-8",
    )
    with pytest.raises(SiteConfigError, match="missing files"):
        _sync_tools(tmp_path, tmp_path / "generated" / "backend", _tools())


@pytest.mark.parametrize(
    ("tools", "message"),
    [
        ({}, "must be a JSON array"),
        ([{"name": "bad-name"}], "valid Python identifier"),
        ([{"name": "run", "inputs": [{"name": "context", "type": "str"}]}], "valid Python identifier"),
        ([{"name": "run", "inputs": [{"name": "value", "type": "unknown"}]}], "must be one of"),
        ([{"name": "run", "inputs": [{"name": "value", "type": []}]}], "must be one of"),
        ([{"name": "run", "permissions": ["owner"]}], "permissions"),
        ([{"name": "first", "handler": "shared"}, {"name": "second", "handler": "shared"}], "duplicates handler"),
    ],
)
def test_invalid_tools_config_is_rejected(tools, message):
    config = json.loads(json.dumps({"tools": tools}))
    with pytest.raises(SiteConfigError, match=message):
        validate_tools_config(config)


@pytest.mark.parametrize(
    ("configured_type", "normalized_type"),
    [
        ("str", "str"),
        ("string", "str"),
        ("bool", "bool"),
        ("boolean", "bool"),
    ],
)
def test_tool_scalar_type_aliases_are_normalized(configured_type, normalized_type):
    config = {
        "tools": [
            {"name": "run", "inputs": [{"name": "value", "type": configured_type}]}
        ]
    }
    validate_tools_config(config)
    assert config["tools"][0]["inputs"][0]["type"] == normalized_type


def test_generated_python_tool_modules_compile():
    tools = _tools()
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    contexts = {
        "tool_registry.py.j2": {
            "tools": tools,
            "tools_json": json.dumps(tools, ensure_ascii=False),
        },
        "tools_api.py.j2": {"tools": tools},
        "tool_execution_handler.py.j2": {},
        "tool_execution_model.py.j2": {},
        "tool_runtime.py.j2": {},
        "background_execution_cleanup.py.j2": {},
    }
    for template_name, context in contexts.items():
        rendered = env.get_template(template_name).render(context)
        compile(rendered, template_name, "exec")


def test_dashboard_renders_tool_region():
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    rendered = env.get_template("dashboard_page.tsx.j2").render(
        models=[],
        scheduled_tasks=[],
        site_logger=False,
        show_dashboard_announcement=False,
        tools=_tools(),
    )
    assert "import { DashboardTools }" in rendered
    assert "<DashboardTools />" in rendered


def test_dashboard_tools_are_rendered_after_scheduled_tasks():
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    rendered = env.get_template("dashboard_page.tsx.j2").render(
        models=[],
        scheduled_tasks=[{"name": "daily_summary"}],
        site_logger=False,
        show_dashboard_announcement=False,
        tools=_tools(),
    )

    scheduled_tasks_position = rendered.index("{/* Scheduled Tasks Section */}")
    edit_modal_position = rendered.index("{/* Edit Task Modal */}")
    tools_position = rendered.index("<DashboardTools />")

    assert scheduled_tasks_position < tools_position < edit_modal_position


def test_dashboard_tools_use_one_section_card_with_tool_items():
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    rendered = env.get_template("frontend_dashboard_tools.tsx.j2").render(
        tools=_tools()
    )

    assert '<section className="overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm">' in rendered
    assert "t('tools.subtitle', 'Run workspace utilities and track their progress')" in rendered
    assert '<form onSubmit={submit} className="group relative overflow-hidden rounded-xl border bg-background p-5 shadow-sm' in rendered
    assert 'const executionStyle = (status: string)' in rendered
    assert 'const ToolExecutionPanel: React.FC' in rendered
    assert "t('tools.files_selected', '{{count}} files selected'" in rendered
    assert 'className="rounded-xl border bg-card p-6 shadow-sm space-y-5"' not in rendered


def test_dashboard_tools_locale_keys_are_generated(tmp_path):
    generate_locale_files([], tmp_path)

    en = json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))
    assert en["tools"]["title"] == "Tools"
    assert zh["tools"]["title"] == "工具"
    assert zh["tools"]["execute"] == "执行"


def test_site_sync_generates_complete_tool_feature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ToolApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "ToolApp"
    config_path = project / "site_config.py"
    config_path.write_text(
        "from onesite.config import SiteConfig\n"
        f"config = SiteConfig(tools={_tools()!r})\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    generated_backend = project / "generated" / "backend" / "app"
    generated_frontend = project / "generated" / "frontend" / "src"
    assert (project / "app" / "tools" / "merge_reports.py").exists()
    assert (generated_backend / "tools" / "merge_reports.py").exists()
    assert (generated_backend / "api" / "endpoints" / "tools.py").exists()
    assert (generated_backend / "handlers" / "tool_execution.py").exists()
    assert (generated_backend / "core" / "background_execution.py").exists()
    assert (generated_backend / "core" / "background_execution_cleanup.py").exists()
    assert (generated_backend / "api" / "endpoints" / "task_center.py").exists()
    assert (generated_frontend / "components" / "dashboard-tools.tsx").exists()
    assert (generated_frontend / "services" / "tools.ts").exists()
    assert (generated_frontend / "pages" / "TaskCenter.tsx").exists()
    routes = (generated_frontend / "Routes.tsx").read_text(encoding="utf-8")
    assert "path: '/task-center'" in routes
    menu = (generated_frontend / "Menu.tsx").read_text(encoding="utf-8")
    assert 'key: "/task-center"' in menu
    main = (generated_backend / "main.py").read_text(encoding="utf-8")
    assert "await cleanup_expired_background_executions()" in main
    assert "run_background_execution_cleanup()" in main

    for python_file in generated_backend.rglob("*.py"):
        compile(python_file.read_text(encoding="utf-8"), str(python_file), "exec")

def test_hidden_tool_is_excluded_from_task_center_api_and_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "HiddenToolApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "HiddenToolApp"
    (project / "site_config.py").write_text(
        "from onesite.config import HiddenTask, SiteConfig, TaskCenterConfig\n"
        "config = SiteConfig(\n"
        "    tools=[{'name': 'internal_cleanup'}],\n"
        "    task_center=TaskCenterConfig(hidden=[\n"
        "        HiddenTask(kind='tool', name='internal_cleanup'),\n"
        "    ]),\n"
        ")\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    generated = project / "generated"
    api = (
        generated / "backend" / "app" / "api" / "endpoints" / "task_center.py"
    ).read_text(encoding="utf-8")
    page = (
        generated / "frontend" / "src" / "pages" / "TaskCenter.tsx"
    ).read_text(encoding="utf-8")
    assert '"kind": "tool", "name": "internal_cleanup"' in api
    assert "internal_cleanup" not in page
