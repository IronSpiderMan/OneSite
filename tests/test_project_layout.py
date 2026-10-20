"""Project layout coverage for OneSite projects."""

from typer.testing import CliRunner

from onesite.main import app
from onesite.project_paths import get_project_paths


def test_create_uses_separate_source_and_generated_directories(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)

    result = CliRunner().invoke(app, ["create", "AlarmApp"])

    assert result.exit_code == 0, result.output
    project = tmp_path / "AlarmApp"
    assert (project / "app" / "models" / "user.py").exists()
    assert (project / "app" / "utils" / "__init__.py").exists()
    assert (project / "app" / "backend" / "api" / "__init__.py").exists()
    assert (project / "app" / "backend" / "services" / "__init__.py").exists()
    assert (project / "app" / "backend" / "cruds" / "__init__.py").exists()
    assert (project / "app" / "resources.py").exists()
    assert (project / "generated" / "backend" / "Dockerfile").exists()
    assert (project / "generated" / "frontend" / "Dockerfile").exists()
    assert (project / "deploy" / ".env.example").exists()
    assert (project / "site_config.py").exists()
    assert not (project / "site_config.json").exists()
    assert not (project / "models").exists()
    assert not (project / "backend").exists()
    assert not (project / "frontend").exists()
    assert not (project / "codegen").exists()


def test_path_resolver_does_not_use_top_level_legacy_directories(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()

    paths = get_project_paths(tmp_path)

    assert paths.models == tmp_path / "app" / "models"
    assert paths.tools == tmp_path / "app" / "tools"
    assert paths.tasks == tmp_path / "app" / "tasks"
    assert paths.cmd == tmp_path / "app" / "cmd"
    assert paths.backend_source == tmp_path / "app" / "backend"
    assert paths.frontend_source == tmp_path / "app" / "frontend"
    assert paths.backend == tmp_path / "generated" / "backend"
    assert paths.frontend == tmp_path / "generated" / "frontend"


def test_path_resolver_uses_modern_layout_when_app_exists(tmp_path):
    (tmp_path / "app").mkdir()

    paths = get_project_paths(tmp_path)

    assert paths.models == tmp_path / "app" / "models"
    assert paths.integrations == tmp_path / "app" / "integrations"
    assert paths.tools == tmp_path / "app" / "tools"
    assert paths.tasks == tmp_path / "app" / "tasks"
    assert paths.cmd == tmp_path / "app" / "cmd"
    assert paths.backend_source == tmp_path / "app" / "backend"
    assert paths.frontend_source == tmp_path / "app" / "frontend"
    assert paths.backend == tmp_path / "generated" / "backend"
    assert paths.frontend == tmp_path / "generated" / "frontend"
    assert paths.deploy == tmp_path / "deploy"


def test_created_project_syncs_into_generated_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    created = runner.invoke(app, ["create", "SyncedApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "SyncedApp"
    utils = project / "app" / "utils"
    utils.mkdir(exist_ok=True)
    (utils / "project_helper.py").write_text(
        "def project_name():\n"
        "    return 'SyncedApp'\n",
        encoding="utf-8",
    )
    custom_api = project / "app" / "backend" / "api" / "health.py"
    custom_api.write_text(
        "from fastapi import APIRouter\n\n"
        "router = APIRouter(prefix='/health', tags=['health'])\n\n"
        "@router.get('')\n"
        "async def health():\n"
        "    return {'status': 'ok'}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])

    assert synced.exit_code == 0, synced.output
    assert (project / "generated" / "backend" / "app" / "main.py").exists()
    assert (project / "generated" / "backend" / "app" / "resources.py").exists()
    assert (
        project
        / "generated"
        / "backend"
        / "app"
        / "utils"
        / "project_helper.py"
    ).exists()
    assert (
        project
        / "generated"
        / "backend"
        / "app"
        / "api"
        / "endpoints"
        / "custom"
        / "health.py"
    ).exists()
    generated_router = (
        project / "generated" / "backend" / "app" / "api" / "api.py"
    ).read_text(encoding="utf-8")
    assert "from app.api.endpoints.custom import health" not in generated_router
    assert (project / "generated" / "frontend" / "src" / "Routes.tsx").exists()
    assert (
        project / "generated" / "frontend" / "src-tauri" / "tauri.conf.json"
    ).exists()
    assert not (project / "backend").exists()
    assert not (project / "frontend").exists()


def test_init_uses_modern_layout_for_an_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)

    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "app" / "models" / "user.py").exists()
    assert (tmp_path / "app" / "resources.py").exists()
    assert (tmp_path / "app" / "backend" / "api" / "__init__.py").exists()
    assert (tmp_path / "deploy" / ".env.example").exists()
    assert not (tmp_path / "models").exists()


def test_init_ignores_top_level_legacy_directories(tmp_path, monkeypatch):
    (tmp_path / "models").mkdir()
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)

    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "models").exists()
    assert (tmp_path / "app" / "models").exists()
